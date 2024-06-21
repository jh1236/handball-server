import re
import time

from FixtureGenerators.FixturesGenerator import get_type_from_name
from structure import get_information
from utils.databaseManager import DatabaseManager
from utils.statistics import calc_elo

SIDES = ["Left", "Right", "Substitute"]


def searchable_of(name: str):
    s = name.lower().replace(" ", "_").replace(",", "").replace("the_", "")
    return re.sub("[^a-zA-Z0-9_]", "", s)

def sync(c, game_id):
    c.execute("""UPDATE games
SET teamOneScore    = lg.teamOneScore,
    teamTwoScore    = lg.teamTwoScore,
    teamOneTimeouts = lg.teamOneTimeouts,
    teamTwoTimeouts = lg.teamTwoTimeouts,
    winningTeam     = lg.winningTeam,
    started         = lg.started,
    ended           = lg.ended,
    protested       = lg.protested,
    resolved        = lg.resolved,
    playerToServe = lg.playerToServe,
    teamToServe = lg.teamToServe,
    sideToServe = lg.sideToServe,
    someoneHasWon = lg.someoneHasWon
FROM liveGames lg
WHERE lg.id = games.id AND games.id = ?;""", (game_id,))
    c.execute("""
    UPDATE playerGameStats
SET points = lg.points,
    aces = lg.aces,
    faults = lg.faults,
    servedPoints = lg.servedPoints,
    servedPointsWon = lg.servedPointsWon,
    servesReceived = lg.servesReceived,
    servesReturned = lg.servesReturned,
    doubleFaults = lg.doubleFaults,
    greenCards = lg.greenCards,
    warnings = lg.warnings,
    yellowCards = lg.yellowCards,
    redCards = lg.redCards,
    cardTimeRemaining = lg.cardTimeRemaining,
    cardTime = lg.cardTime,
    roundsBenched = lg.roundsBenched,
    roundsPlayed = lg.roundsPlayed
FROM livePlayerGameStats lg
WHERE playerGameStats.id = lg.id
        AND playerGameStats.gameId = ?;
""", (game_id,))


def game_string_lookup(char: str):
    d = {
        "s": "Score",
        "a": "Ace",
        "g": "Green Card",
        "y": "Yellow Card",
        "v": "Red Card",
        "f": "Fault",
        "t": "Timeout",
        "x": "Substitute",
        "e": "Forfeit"
    }
    if char in d:
        return d[char]
    if char.isdigit():
        return "Yellow Card"
    return None


def _team_and_position_to_id(game_id, first_team, left_player, c) -> int:
    if first_team:
        player = c.execute("""
SELECT playerGameStats.playerId
FROM games
         INNER JOIN gameEvents ON gameEvents.id = (SELECT max(id) FROM gameEvents WHERE games.id = gameEvents.gameId)
         INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND playerGameStats.teamId = games.teamOne
         WHERE games.id = ?
         ORDER BY teamOneLeft = playerGameStats.playerId = ? DESC
""", (game_id, left_player)).fetchone()
        player = player[0]
    else:
        player = c.execute("""SELECT playerGameStats.playerId
FROM games
         INNER JOIN gameEvents ON gameEvents.id = (SELECT max(id) FROM gameEvents WHERE games.id = gameEvents.gameId)
         INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND playerGameStats.teamId = games.teamTwo
         WHERE games.id = ?
         ORDER BY (teamTwoLeft = playerGameStats.playerId) = ? DESC
        """, (game_id, left_player)).fetchone()[0]
    return player


def _tournament_from_game(game_id, c):
    return c.execute("""SELECT tournamentId FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def _swap_server(game_id, team_to_serve, c, swap=True):
    query = c.execute(
        """SELECT sideServed FROM gameEvents WHERE gameId = ? AND teamWhoServed = ? ORDER BY id DESC LIMIT 1""",
        (game_id, team_to_serve)).fetchone()

    if query is None:  # this team is yet to serve
        old_side = "Right" if swap else "Left"
    else:
        old_side = query[0]
    if swap:
        if old_side == "Left":
            new_side = "Right"
        else:
            new_side = "Left"
    else:
        new_side = old_side
    player_to_serve = c.execute(
        """SELECT playerGameStats.playerId,
       (teamOneLeft = playerGameStats.playerId OR teamTwoLeft = playerGameStats.playerId) = (? = 'Left') as o
FROM games
         INNER JOIN gameEvents ON gameEvents.id = (SELECT MAX(id) FROM gameEvents WHERE gameEvents.gameId = games.id)
         INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND (teamOneLeft = playerGameStats.playerId OR
                                                                              teamOneRight = playerGameStats.playerId OR
                                                                              teamTwoLeft = playerGameStats.playerId OR
                                                                              teamTwoRight = playerGameStats.playerId)
WHERE games.id = ?
  AND playerGameStats.teamId = ?
  AND cardTimeRemaining = 0
ORDER BY o desc""",
        (new_side, game_id, team_to_serve)).fetchall()
    if not player_to_serve:
        return None, None
    return player_to_serve[0][0], new_side


def game_is_over(game_id, c):
    return c.execute("""SELECT someoneHasWon FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def game_is_ended(game_id, c):
    return c.execute("""SELECT ended FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def game_has_started(game_id, c):
    return c.execute("""SELECT started FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def _score_point(game_id, c, first_team, left_player, penalty=False, points = 1):
    if game_is_over(game_id, c):
        raise ValueError("Game is Already Over!")
    for _ in range(points):
        _add_to_game(game_id, c, "Score", first_team, left_player, team_to_serve=first_team,
                     notes="Penalty" if penalty else None)
    if penalty:
        sync(c, game_id)


def _get_serve_details(game_id, c):
    a = c.execute(
        """SELECT nextTeamToServe,nextPlayerToServe,nextServeSide from gameEvents WHERE gameEvents.gameId = ? order by id DESC LIMIT 1""",
        (game_id,)).fetchone()
    return tuple(a)


def _get_player_details(game_id, c):
    a = c.execute(
        """SELECT teamOneLeft, teamOneRight, teamTwoLeft, teamTwoRight from gameEvents WHERE gameEvents.gameId = ? order by id DESC LIMIT 1""",
        (game_id,)).fetchone()
    return tuple(a)


def _add_to_game(game_id, c, char: str, first_team, left_player, team_to_serve=None, details=None, notes=None):
    """IMPORTANT: if the item added to game is a penalty, THE CALLER IS RESPONSIBLE FOR SYNCING"""
    player = _team_and_position_to_id(game_id, first_team, left_player, c) if left_player is not None else None
    team = get_information.get_team_id_from_game_and_side(game_id, first_team, c) if first_team is not None else None
    next_team_to_serve = None if team_to_serve is None else get_information.get_team_id_from_game_and_side(game_id, team_to_serve, c)
    players = _get_player_details(game_id, c)
    tournament = _tournament_from_game(game_id, c)
    team_who_served, player_who_served, serve_side = _get_serve_details(game_id, c)
    next_team_to_serve = next_team_to_serve or team_who_served
    swap = team_who_served != next_team_to_serve
    if swap:
        next_player_to_serve, next_serve_side = _swap_server(game_id, next_team_to_serve, c,
                                                             swap=swap)
    else:
        next_player_to_serve, next_serve_side = player_who_served, serve_side
    c.execute("""INSERT INTO gameEvents(gameId, teamId, playerId, tournamentId, eventType, time, details, notes, teamWhoServed,playerWhoServed,  sideServed, nextTeamToServe, nextPlayerToServe, nextServeSide, teamOneLeft, teamOneRight, teamTwoLeft, teamTwoRight)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?)""", (
        game_id, team if team is not None else None, player if player is not None else None, tournament,
        char, time.time(),
        details, notes,
        team_who_served, player_who_served, serve_side,
        next_team_to_serve, next_player_to_serve, next_serve_side, players[0], players[1], players[2], players[3]))
    if char == "Substitute":
        player_on = c.execute("""SELECT playerGameStats.playerid
FROM playerGameStats
         INNER JOIN gameEvents
                    ON gameEvents.id = (SELECT MAX(id) FROM gameEvents WHERE gameEvents.gameId = playerGameStats.gameId)
WHERE playerGameStats.gameId = ?
  AND playerGameStats.teamId = ?
  AND gameEvents.teamOneLeft <> playerGameStats.playerId
  AND gameEvents.teamOneRight <> playerGameStats.playerId
  AND gameEvents.teamTwoLeft <> playerGameStats.playerId
  AND gameEvents.teamTwoRight <> playerGameStats.playerId""", (game_id, team)).fetchone()[0]
        if first_team:
            if left_player:
                c.execute(
                    """UPDATE gameEvents SET teamOneLeft = ? WHERE id = (SELECT MAX(id) FROM gameEvents WHERE gameId = ?)""",
                    (player_on, game_id,))
            else:
                c.execute(
                    """UPDATE gameEvents SET teamOneRight = ? WHERE id = (SELECT MAX(id) FROM gameEvents WHERE gameId = ?)""",
                    (player_on, game_id,))
        else:
            if left_player:
                c.execute(
                    """UPDATE gameEvents SET teamTwoLeft = ? WHERE id = (SELECT MAX(id) FROM gameEvents WHERE gameId = ?)""",
                    (player_on, game_id,))
            else:
                c.execute(
                    """UPDATE gameEvents SET teamTwoRight = ? WHERE id = (SELECT MAX(id) FROM gameEvents WHERE gameId = ?)""",
                    (player_on, game_id,))

    if notes != "Penalty":
        sync(c, game_id)
        if "Card" in char or char == "Substitute":
            next_player_to_serve, next_serve_side = _swap_server(game_id, next_team_to_serve, c,
                                                                 swap=team_who_served != next_team_to_serve)
            c.execute(
                """UPDATE gameEvents SET nextTeamToServe = ? ,nextPlayerToServe = ?, nextServeSide = ? WHERE id = (SELECT MAX(id) FROM gameEvents WHERE gameId = ?)""",
                (next_team_to_serve, next_player_to_serve, next_serve_side, game_id,))
            sync(c, game_id)


def start_game(game_id, swap_service, team_one, team_two, team_one_iga, official=None, scorer=None):
    with DatabaseManager() as c:
        if game_has_started(game_id, c):
            raise ValueError("Game is already started!")
        tournament = _tournament_from_game(game_id, c)
        team_one_id, team_two_id = c.execute("""SELECT teamOne, teamTwo FROM games WHERE games.id = ?""",
                                             (game_id,)).fetchone()

        if team_one is None:
            team_one = [i[0] for i in c.execute(
                """SELECT people.searchableName FROM games INNER JOIN teams ON teams.id = games.teamOne INNER JOIN people ON 
                (captain = people.id OR noncaptain = people.id OR substitute = people.id) WHERE games.id = ?""",
                (game_id,)).fetchall() if i]
        if team_two is None:
            team_two = [i[0] for i in c.execute(
                """SELECT people.searchableName FROM games INNER JOIN teams ON teams.id = games.teamTwo INNER JOIN people ON 
                (captain = people.id OR noncaptain = people.id OR substitute = people.id) WHERE games.id = ?""",
                (game_id,)).fetchall() if i]
        get_information.game_and_side[game_id] = (team_one_id, team_two_id)
        team_one_players = []
        for name in team_one:
            team_one_players.append(c.execute("""
                SELECT id FROM people WHERE searchableName = ?""",
                                              (name,)).fetchone()[0])
        team_one_players += [None]
        team_two_players = []
        for name in team_two:
            team_two_players.append(c.execute("""
                SELECT id FROM people WHERE searchableName = ?""",
                                              (name,)).fetchone()[0])
        team_two_players += [None]
        print(f"{team_one_players = }, {team_two_players = }")
        iga = team_one_id if team_one_iga else team_two_id
        c.execute(
            """UPDATE games SET status = 'In Progress', adminStatus = 'In Progress', startTime = ?, IGASide = ? where id = ?""",
            (time.time(), iga, game_id,))
        if official:
            c.execute("""
                UPDATE games SET official = 
                (SELECT officials.id
                 from officials INNER JOIN people on personId = people.id where people.searchableName = ?) 
                 where id = ?""", (official, game_id))
        if scorer:
            c.execute("""
                UPDATE games SET scorer = 
                (SELECT officials.id
                 from officials INNER JOIN people on personId = people.id where people.searchableName = ?) 
                 where id = ?""", (scorer, game_id))
        for name, side in zip(team_one, SIDES):
            c.execute("""
                UPDATE playerGameStats SET startSide = ? 
                where 
                    playerGameStats.playerId = (SELECT people.id from people where people.searchableName = ?) and
                    playerGameStats.gameId = ?""",
                      (side, name, game_id))
        for name, side in zip(team_two, SIDES):
            c.execute("""
                    UPDATE playerGameStats SET startSide = ? 
                    where 
                        playerGameStats.playerId = (SELECT people.id from people where people.searchableName = ?) and
                        playerGameStats.gameId = ?""",
                      (side, name, game_id))
        team = get_information.get_team_id_from_game_and_side(game_id, not swap_service, c=c)
        c.execute("""INSERT
    INTO gameEvents(gameId, tournamentId, eventType, time,nextPlayerToServe, nextTeamToServe, nextServeSide, teamOneLeft, teamOneRight,
                    teamTwoLeft, teamTwoRight)
    VALUES (?, ?, 'Start', ?, ?, ?, 'Left', ?, ?, ?, ?)""",
                  (game_id, tournament, time.time(), team_two_players[0] if swap_service else team_one_players[0], team,
                   team_one_players[0], team_one_players[1], team_two_players[0], team_two_players[1]))
        sync(c, game_id)


def score_point(game_id, first_team, left_player):
    with DatabaseManager() as c:
        if game_is_over(game_id, c):
            raise ValueError("Game is Already Over!")
        _score_point(game_id, c, first_team, left_player)


def ace(game_id):
    with DatabaseManager() as c:
        if game_is_over(game_id, c):
            raise ValueError("Game is Already Over!")
        first_team = bool(
            c.execute("""SELECT teamOne == teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone()[
                0])
        left_player = bool(c.execute(
            """SELECT sideToServe = 'Left' FROM games WHERE games.id = ?""",
            (game_id,)).fetchone()[0])
        _add_to_game(game_id, c, "Ace", first_team, left_player)
        _score_point(game_id, c, first_team, left_player, penalty=True)


def fault(game_id):
    with DatabaseManager() as c:
        if game_is_over(game_id, c):
            raise ValueError("Game is Already Over!")
        first_team = bool(
            c.execute("""SELECT teamOne = teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone()[
                0])
        left_player = bool(c.execute(
            """SELECT sideToServe = 'Left' FROM games WHERE games.id = ?""",
            (game_id,)).fetchone()[0])
        prev_event = c.execute(
            """SELECT eventType FROM gameEvents WHERE gameId = ? AND (eventType = 'Score' or eventType = 'Fault') ORDER BY id DESC LIMIT 1""",
            (game_id,)).fetchone()
        _add_to_game(game_id, c, "Fault", first_team, left_player)
        if prev_event:
            prev_event = prev_event[0]
        if prev_event == "Fault":
            _score_point(game_id, c, not first_team, None, penalty=True)


def card(game_id, first_team, left_player, color, duration, reason):
    with DatabaseManager() as c:
        if color in ["Green", "Yellow", "Red"]:
            color += " Card"
        _add_to_game(game_id, c, color, first_team, left_player, notes=reason, details=duration)
        team = get_information.get_team_id_from_game_and_side(game_id, first_team, c)
        both_carded = c.execute(
            """SELECT MIN(iif(cardTimeRemaining < 0, 12, cardTimeRemaining))
FROM games
         INNER JOIN main.gameEvents gE on gE.id = (SELECT MAX(id) FROM gameEvents WHERE games.id = gE.gameId)
         INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND (teamOneLeft = playerGameStats.playerId OR
                                                                              teamOneRight = playerGameStats.playerId OR
                                                                              teamTwoLeft = playerGameStats.playerId OR
                                                                              teamTwoRight = playerGameStats.playerId)
WHERE playerGameStats.gameId = ?
  AND playerGameStats.teamId = ?""",
            (game_id, team)).fetchone()[0]
        if both_carded != 0:
            my_score, their_score, someone_has_won = c.execute(
                """SELECT teamOneScore, teamTwoScore, someoneHasWon FROM games WHERE games.id = ?""",
                (game_id,)).fetchone()
            if someone_has_won:
                return
            if not first_team:
                my_score, their_score = their_score, my_score
            both_carded = min(both_carded, max(11 - their_score, my_score + 2 - their_score))
            _score_point(game_id, c, not first_team, None, penalty=True, points=both_carded)


def undo(game_id):
    with DatabaseManager() as c:
        if game_is_ended(game_id, c):
            raise ValueError("Game has been set to official!")
        c.execute("""DELETE FROM gameEvents 
                 WHERE 
                   gameId = ? AND
                   id >= ( 
                      SELECT t.ID
                        FROM
                            gameEvents t
                        WHERE t.gameId = gameEvents.gameId AND (t.notes IS NULL or t.notes <> 'Penalty') AND t.eventType <> 'Protest' AND t.eventType <> 'End Game'
                        ORDER BY
                            t.id DESC
                        LIMIT 1
                    )""", (game_id,))
        sync(c, game_id)


def change_code(game_id):
    with DatabaseManager() as c:
        return (c.execute("""SELECT id 
                          FROM 
                             gameEvents
                          WHERE gameId = ? 
                          ORDER BY 
                             id DESC
                          LIMIT 1""", (game_id,)).fetchone() or [0])[0]


def time_out(game_id, first_team):
    with DatabaseManager() as c:
        if game_is_over(game_id, c):
            raise ValueError("Game is Already Over!")
        _add_to_game(game_id, c, "Timeout", first_team, None)


def forfeit(game_id, first_team):
    with DatabaseManager() as c:
        if game_is_over(game_id, c):
            raise ValueError("Game is Already Over!")
        _add_to_game(game_id, c, "Forfeit", first_team, None)


def end_timeout(game_id):
    with DatabaseManager() as c:
        if game_is_over(game_id, c):
            raise ValueError("Game is Already Over!")
        _add_to_game(game_id, c, "End Timeout", None, None)


def end_game(game_id, bestPlayer,
             notes, protest_team_one, protest_team_two):
    with DatabaseManager() as c:
        tournament_id = c.execute("""SELECT tournamentId FROM games WHERE id = ?""", (game_id,)).fetchone()[0]
        best = c.execute("""SELECT id FROM people WHERE searchableName = ?""", (bestPlayer,)).fetchone()
        if best:
            best = best[0]
        else:
            allowed = c.execute("""SELECT SUM(eventType = 'Forfeit') > 0 FROM gameEvents WHERE gameId = ?""",
                                (game_id,)).fetchone()[0]
            allowed |= bool(c.execute("""SELECT teams.id FROM games INNER JOIN teams ON 
            (teams.id = games.teamOne or games.teamTwo = teams.id) WHERE (teams.nonCaptain is null) AND games.id = ?""", (game_id,)).fetchone())
            if not allowed:
                raise ValueError("Best Player was not provided")
        if protest_team_one:
            _add_to_game(game_id, c, "Protest", True, None, notes=protest_team_one)
        if protest_team_two:
            _add_to_game(game_id, c, "Protest", False, None, notes=protest_team_two)
        _add_to_game(game_id, c, "End Game", None, None, notes=notes, details=best)
        teams = c.execute("""
SELECT games.isRanked as ranked,
       games.winningTeam = teamId as myTeamWon,
       games.teamOne <> playerGameStats.teamId as isSecond,
       ROUND(1500.0 + coalesce((SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = playerGameStats.playerid), 0), 2) as elo,
       playerId as player
       FROM playerGameStats
         INNER JOIN games ON playerGameStats.gameId = games.id
WHERE games.id = ? ORDER BY isSecond""", (game_id,)).fetchall()

        protested, red_cards, yellow_cards, start_time = c.execute("""SELECT protested,
       SUM(playerGameStats.redCards) > 0,
       SUM(playerGameStats.yellowCards) > 0,
       startTime
FROM games
         INNER JOIN main.playerGameStats on playerGameStats.gameId = games.id
         WHERE games.id = ?""", (game_id,)).fetchone()

        if red_cards:
            c.execute("""UPDATE games SET adminStatus = 'Red Card Awarded' WHERE id = ?""", (game_id,))
        elif protested:
            c.execute("""UPDATE games SET adminStatus = 'Protested' WHERE id = ?""", (game_id,))
        elif notes.strip():
            c.execute("""UPDATE games SET adminStatus = 'Notes To Review' WHERE id = ?""", (game_id,))
        elif yellow_cards:
            c.execute("""UPDATE games SET adminStatus = 'Yellow Card Awarded' WHERE id = ?""", (game_id,))
        else:
            c.execute("""UPDATE games SET adminStatus = 'Official' WHERE id = ?""", (game_id,))
        end_time = time.time() - start_time

        c.execute("""UPDATE games SET status = 'Official', noteableStatus = adminStatus, length = ?, bestPlayer = ?, notes = ? WHERE id = ?""", (end_time, best, notes.strip(), game_id,))

        c.execute("""UPDATE playerGameStats SET isBestPlayer = (SELECT games.bestPlayer = playerGameStats.playerId FROM games WHERE games.id = playerGameStats.gameId) WHERE playerGameStats.gameid = ?""", (game_id,))

        if teams[0][0]:  # the game is unranked, so doing elo stuff is silly
            elos = [0, 0]
            team_sizes = [0, 0]
            for i in teams:
                elos[i[2]] += i[3]
                team_sizes[i[2]] += 1
            for i, v in enumerate(team_sizes):
                elos[i] /= v
            print(elos)
            for i in teams:
                win = i[1]
                my_team = i[2]
                player_id = i[4]
                elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
                c.execute("""INSERT INTO eloChange(gameId, playerId, tournamentId, eloChange) VALUES (?, ?, ?, ?)""",
                          (game_id, player_id, tournament_id, elo_delta))
        end_of_round = c.execute(
            """SELECT id FROM games WHERE not games.isBye AND games.tournamentId = ? AND not games.ended""",
            (tournament_id,)).fetchone()
        fixture_gen, finals_gen, in_finals, finished = c.execute(
            """SELECT fixturesGenerator, finalsGenerator, inFinals, isFinished FROM tournaments WHERE tournaments.id = ?""",
            (tournament_id,)).fetchone()

        sync(c, game_id)

    if not end_of_round:
        if not in_finals:
            fixtures = get_type_from_name(fixture_gen, tournament_id)
            fixtures.end_of_round()
            with DatabaseManager() as c:
                in_finals = c.execute("""SELECT inFinals FROM tournaments WHERE tournaments.id = ?""",
                                      (tournament_id,)).fetchone()[0]
        if in_finals and not finished:
            print(in_finals)
            print(finished)
            finals = get_type_from_name(finals_gen, tournament_id)
            finals.end_of_round()



def substitute(game_id, first_team, left_player):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, "Substitute", first_team, left_player)



def create_game(tournamentId, team_one, team_two, official=None, players_one=None, players_two=None, round_number=-1,
                court=0, is_final=False):
    """Pass team_one & team_two in as either int (team id) or str (searchableName)."""
    with DatabaseManager() as c:
        if isinstance(tournamentId, str):
            tournamentId = \
                c.execute("""SELECT id FROM tournaments WHERE tournaments.searchableName = ?""",
                          (tournamentId,)).fetchone()[0]
        if players_one is not None:
            players = [None, None, None]
            for i, v in enumerate(players_one):
                players[i] = c.execute("""SELECT id FROM people WHERE people.searchableName = ?""", (v,)).fetchone()[0]
            print(players)
            first_team = c.execute("""SELECT id
FROM teams
WHERE (captain = ? or nonCaptain = ? or substitute = ?)
  AND IIF(? is null, 1, (captain = ? or nonCaptain = ? or substitute = ?))
  AND IIF(? is null, 1, (captain = ? or nonCaptain = ? or substitute = ?))
""",
                                   (players[0], players[0], players[0], players[1], players[1], players[1], players[1],
                                    players[2],
                                    players[2], players[2], players[2])).fetchone()
            if first_team:
                first_team = first_team[0]
            else:
                c.execute(
                    """INSERT INTO teams(name, searchableName, captain, nonCaptain, substitute) VALUES (?, ?, ?, ?, ?)""",
                    (team_one, searchable_of(team_one), players[0], players[1], players[2]))
                first_team = c.execute("""SELECT id FROM teams ORDER BY id DESC LIMIT 1""").fetchone()[0]
        else:
            if isinstance(team_one, int):
                first_team = team_one
            else:
                first_team = c.execute("""SELECT id FROM teams WHERE searchableName = ?""", (team_one,)).fetchone()[0]
        if players_two is not None:
            players = [None, None, None]
            for i, v in enumerate(players_two):
                players[i] = c.execute("""SELECT id FROM people WHERE people.searchableName = ?""", (v,)).fetchone()[0]

            second_team = c.execute("""SELECT id
FROM teams
WHERE (captain = ? or nonCaptain = ? or substitute = ?)
  AND IIF(? is null, 1, (captain = ? or nonCaptain = ? or substitute = ?))
  AND IIF(? is null, 1, (captain = ? or nonCaptain = ? or substitute = ?))
""",
                                    (players[0], players[0], players[0], players[1], players[1], players[1], players[1],
                                     players[2],
                                     players[2], players[2], players[2])).fetchone()
            if second_team:
                second_team = second_team[0]
            else:
                c.execute(
                    """INSERT INTO teams(name, searchableName, captain, nonCaptain, substitute) VALUES (?, ?, ?, ?, ?)""",
                    (team_two, searchable_of(team_two), players[0], players[1], players[2]))
                second_team = c.execute("""SELECT id FROM teams ORDER BY id DESC LIMIT 1""").fetchone()[0]
        else:
            if isinstance(team_two, int):
                second_team = team_two
            else:
                second_team = c.execute("""SELECT id FROM teams WHERE searchableName = ?""", (team_two,)).fetchone()[0]

        ranked = True

        for i in [first_team, second_team]:
            if i == 1: continue
            if c.execute("""SELECT id FROM tournamentTeams WHERE teamId = ? AND tournamentId = ?""",
                         (i, tournamentId)).fetchone() is None:
                c.execute(
                    """INSERT INTO tournamentTeams(tournamentId, teamId, gamesWon, gamesPlayed, gamesLost, timeoutsCalled) VALUES (?, ?, 0, 0, 0, 0)""",
                    (
                        tournamentId, i
                    ))
            ranked &= c.execute(
                """SELECT teams.nonCaptain FROM teams WHERE teams.id = ?""",
                (i,)).fetchone()[0] != None
        if official is not None:
            official = c.execute(
                """SELECT officials.id FROM officials INNER JOIN people ON personId = people.id WHERE searchableName = ?""",
                (official,)).fetchone()[0]

        if round_number < 0:
            last_start = c.execute(
                """SELECT startTime, round FROM games WHERE tournamentId = ? ORDER BY id DESC LIMIT 1""",
                (tournamentId,)).fetchone()
            if not last_start:
                last_start, round_number = (-1, 0)
            else:
                last_start, round_number = last_start
            last_start = last_start or 1
            if (
                    time.time()
                    - last_start
                    > 32400 and
                    round_number < 0
            ):
                round_number = round_number + 1
        is_bye = 1 in [first_team, second_team]
        court = -1 if is_bye else court
        if is_bye and first_team == 1:
            first_team, second_team = second_team, first_team

        c.execute("""
            INSERT INTO games(tournamentId, teamOne, teamTwo, official, IGASide, gameStringVersion, gameString, court, isFinal, round, isBye, status, isRanked, teamOneScore, teamTwoScore, teamOneTimeouts, teamTwoTimeouts, started, ended) 
            VALUES (?, ?, ?, ?, ?, 1, '', ?, ?, ?, ?, 'Waiting For Start', ?, 0, 0, 0, 0, ?, ?)
        """, (
            tournamentId, first_team, second_team, official, first_team, court, is_final, round_number, is_bye, ranked,
            is_bye, is_bye))
        game_id = c.execute("""SELECT id from games order by id desc limit 1""").fetchone()[0]
        for i, opp in [(first_team, second_team), (second_team, first_team)]:
            players = c.execute(
                """SELECT people.id FROM people INNER JOIN teams ON people.id = teams.captain or people.id = teams.nonCaptain or people.id = teams.substitute WHERE teams.id = ?""",
                (i,)).fetchall()
            for j in players:
                c.execute(
                    """INSERT INTO playerGameStats(gameId, playerId, teamId, opponentId, tournamentId, roundsPlayed, roundsBenched, isBestPlayer) VALUES (?, ?, ?, ?, ?, 0, 0, 0)""",
                    (game_id, j[0], i, opp, tournamentId))
        return game_id


def create_tournament(name, fixtures_gen, finals_gen, ranked, two_courts, scorer, teams: list[int] = None,
                      officials: list[int] = None):
    officials = officials or []
    teams = teams or []
    with DatabaseManager() as c:
        searchable_name = searchable_of(name)
        c.execute("""INSERT INTO tournaments(name, searchableName, fixturesGenerator, finalsGenerator, ranked, twoCourts,  hasScorer, imageURL, isFinished, isPooled, notes, inFinals) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, '', 0)""", (
            name, searchable_name, fixtures_gen, finals_gen, ranked, two_courts, scorer,
            '/api/tournaments/image?name=' + searchable_name))
        tournament = c.execute("""SELECT id FROM tournaments ORDER BY id desc LIMIT 1""").fetchone()[0]
        for i in teams:
            c.execute(
                """INSERT INTO tournamentTeams(tournamentId, teamId, gamesWon, gamesPlayed, gamesLost, timeoutsCalled, pool) VALUES (?, ?, 0, 0, 0, 0, 0)""",
                (tournament, i))
        for i in officials:
            c.execute(
                """INSERT INTO tournamentOfficials(tournamentId, officialId, isUmpire, isScorer) VALUES (?, ?, 1, 1)""",
                (tournament, i))
    fixtures = get_type_from_name(fixtures_gen, tournament)
    fixtures.begin_tournament()


def get_timeout_time(game_id):
    """Returns the time which the timeout expires"""
    with DatabaseManager() as c:
        time_out_time = (c.execute("""SELECT time
                    FROM gameEvents
                    WHERE gameId = ?
                      AND eventType = 'Timeout'
                      AND not EXISTS(SELECT id
                                     FROM gameEvents i
                                     WHERE i.id > gameEvents.id
                                     AND i.gameId = gameEvents.gameId
                                       AND i.eventType = 'End Timeout')""", (game_id,)).fetchone() or [-1])[0]
        return time_out_time + 30 if (time_out_time > 0) else 0


def get_timeout_caller(game_id):
    """Returns if the first team listed called the timeout"""
    with DatabaseManager() as c:
        time_out_time = (c.execute("""SELECT teamId == games.teamOne
                    FROM gameEvents INNER join games on gameEvents.gameId = games.id
                    WHERE games.Id = ?
                      AND eventType = 'Timeout'
                      AND not EXISTS(SELECT i.id
                                     FROM gameEvents i
                                     WHERE i.id > gameEvents.id
                                     AND i.gameId = gameEvents.gameId
                                       AND i.eventType = 'End Timeout') ORDER BY gameEvents.id desc LIMIT 1""",
                                   (game_id,)).fetchone() or [0])[0]
        return time_out_time


def delete(game_id):
    with DatabaseManager() as c:
        c.execute("""DELETE FROM playerGameStats WHERE playerGameStats.gameId = ?""", (game_id,))
        c.execute("""DELETE FROM gameEvents WHERE gameEvents.gameId = ?""", (game_id,))
        c.execute("""DELETE FROM games WHERE games.id = ?""", (game_id,))


def resolve_game(game_id):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, "Resolve", None, None)
        c.execute("""UPDATE games SET adminStatus = 'Resolved' WHERE id = ?""", (game_id,))
