import re
import time

from structure import get_information
from utils.databaseManager import DatabaseManager
from utils.statistics import calc_elo

SIDES = ["Left", "Right", "Substitute"]


def searchable_of(name: str):
    s = name.lower().replace(" ", "_").replace(",", "").replace("the_", "")
    return re.sub("[^a-zA-Z0-9_]", "", s)


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
            SELECT playerId
            FROM games
                     INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND games.teamOne = playerGameStats.teamId
            AND sideOfCourt = ? and games.id = ?""", (SIDES[not left_player], game_id)).fetchone()
        player = player[0]
    else:
        player = c.execute("""
            SELECT playerId
            FROM games
                INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND games.teamTwo = playerGameStats.teamId
            WHERE sideOfCourt = ? and games.id = ?""", (SIDES[not left_player], game_id)).fetchone()[0]
    return player


def _tournament_from_game(game_id, c):
    return c.execute("""SELECT tournamentId FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def _swap_server(game_id, team_to_serve, c):
    old_side = c.execute(
        """SELECT sideServed FROM gameEvents WHERE gameId = ? AND teamWhoServed = ? ORDER BY id DESC LIMIT 1""",
        (game_id, team_to_serve)).fetchone()
    if old_side is None:
        old_side = "Right"
    else:
        old_side = old_side[0]
    if old_side == "Left":
        new_side = "Right"
    else:
        new_side = "Left"
    player_to_serve = c.execute(
        """SELECT playerId, sideOfCourt = ? as o  FROM playerGameStats WHERE gameId = ? AND teamId = ? AND cardTimeRemaining = 0 ORDER BY o desc""",
        (new_side, game_id, team_to_serve)).fetchall()
    return player_to_serve[0][0], new_side


def game_is_over(game_id, c):
    return c.execute("""SELECT someoneHasWon FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def game_is_ended(game_id, c):
    return c.execute("""SELECT ended FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def game_has_started(game_id, c):
    return c.execute("""SELECT started FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def _score_point(game_id, c, first_team, left_player, penalty=False):
    if game_is_over(game_id, c):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, c, "Score", first_team, left_player, team_to_serve=first_team,
                 notes="Penalty" if penalty else None)


def _get_serve_details(game_id, c):
    a = c.execute(
        """SELECT nextTeamToServe,nextPlayerToServe,nextServeSide from gameEvents WHERE gameEvents.gameId = ? order by id DESC LIMIT 1""",
        (game_id,)).fetchone()
    return tuple(a)


def _add_to_game(game_id, c, char: str, first_team, left_player, team_to_serve=None, details=None, notes=None):
    player = _team_and_position_to_id(game_id, first_team, left_player, c) if left_player is not None else None
    team = get_information.get_team_id_from_game_and_side(game_id, first_team, c) if first_team is not None else None
    next_team_to_serve = get_information.get_team_id_from_game_and_side(game_id, team_to_serve, c)
    tournament = _tournament_from_game(game_id, c)
    team_who_served, player_who_served, serve_side = _get_serve_details(game_id, c)
    if team_to_serve is None or team_who_served == next_team_to_serve:
        next_team_to_serve, next_player_to_serve, next_serve_side = team_who_served, player_who_served, serve_side
    else:
        next_player_to_serve, next_serve_side = _swap_server(game_id, next_team_to_serve, c)

    c.execute("""INSERT INTO gameEvents(gameId, teamId, playerId, tournamentId, eventType, time, details, notes, teamWhoServed,playerWhoServed,  sideServed, nextTeamToServe, nextPlayerToServe, nextServeSide)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?)""", (
        game_id, team if team is not None else None, player if player is not None else None, tournament,
        char, time.time(),
        details, notes,
        team_who_served, player_who_served, serve_side,
        next_team_to_serve, next_player_to_serve, next_serve_side))



def start_game(game_id, swap_service, team_one, team_two, team_one_iga, official=None, scorer=None):
    with DatabaseManager() as c:
        if game_has_started(game_id, c):
            raise ValueError("Game is Already Over!")
        tournament = _tournament_from_game(game_id, c)
        team_one_id, team_two_id = c.execute("""SELECT teamOne, teamTwo FROM games WHERE games.id = ?""",
                                             (game_id,)).fetchone()

        get_information.game_and_side[game_id] = (team_one_id, team_two_id)

        iga = team_one_id if team_one_iga else team_two_id
        c.execute(
            """UPDATE games SET status = adminStatus = 'In Progress', startTime = ?, IGASide = ? where id = ?""",
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
                UPDATE playerGameStats SET sideOfCourt = ? 
                where 
                    playerGameStats.playerId = (SELECT people.id from people where people.searchableName = ?) and
                    playerGameStats.gameId = ?""",
                      (side, name, game_id))
        for name, side in zip(team_two, SIDES):
            c.execute("""
                UPDATE playerGameStats SET sideOfCourt = ? 
                where 
                    playerGameStats.playerId = (SELECT people.id from people where people.searchableName = ?) and
                    playerGameStats.gameId = ?""",
                      (side, name, game_id))
        c.execute("""INSERT INTO gameEvents(gameId, tournamentId, eventType, time, nextPlayerToServe, nextTeamToServe, nextServeSide)
                 SELECT games.id, ?, 'Start', ?, playerGameStats.playerId, playerGameStats.teamId, 'Left'
                 FROM games
                          INNER JOIN playerGameStats ON playerGameStats.gameId = games.id
                     AND sideOfCourt = 'Left' AND (playerGameStats.teamId <> games.teamOne) = ?
                 WHERE games.id = ?""", (tournament, time.time(), swap_service, game_id))


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
            """SELECT MIN(iif(cardTimeRemaining < 0, 12, cardTimeRemaining)) FROM playerGameStats WHERE playerGameStats.gameId = ? AND playerGameStats.teamId = ?""",
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
            for _ in range(both_carded):
                _score_point(game_id, c, not first_team, None, penalty=True)


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


def end_game(game_id, bestPlayer, notes, protest_team_one, protest_team_two):
    with DatabaseManager() as c:
        if protest_team_one:
            _add_to_game(game_id, c, "Protest", True, None, notes=protest_team_one)
        if protest_team_two:
            _add_to_game(game_id, c, "Protest", False, None, notes=protest_team_two)
        if bestPlayer is None:
            allowed = c.execute("""SELECT SUM(eventType = 'Forfeit') > 0 FROM gameEvents WHERE gameId = ?""",
                                (game_id,)).fetchone()[0]
            allowed |= \
                c.execute(
                    """SELECT COUNT(DISTINCT playerID) < 2 FROM playerGameStats WHERE gameId = ? GROUP BY teamId""",
                    (game_id,)).fetchone()[0]
            if not allowed:
                raise ValueError("Best Player was not provided")
        best = c.execute("""SELECT id FROM people WHERE searchableName = ?""", (bestPlayer,)).fetchone()
        if best:
            best = best[0]
        _add_to_game(game_id, c, "End Game", None, None, notes=notes, details=best)
        teams = c.execute("""
SELECT games.isRanked as ranked,
       games.winningTeam = teamId as myTeamWon,
       games.teamOne <> playerGameStats.teamId as isSecond,
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = playerGameStats.playerid), 2) as elo,
       playerId as player,
       games.tournamentId as tournament
FROM playerGameStats
         INNER JOIN games ON playerGameStats.gameId = games.id
WHERE games.id = ? ORDER BY isSecond""", (game_id,)).fetchall()

        if teams[0][0]:  # the game is unranked, so doing elo stuff is silly
            return
        elos = [0, 0]
        team_sizes = [0, 0]
        for i in teams:
            elos[i[2]] += i[3]
            team_sizes[i[2]] += 1
        for i, v in enumerate(team_sizes):
            elos[i] /= v
        for i in teams:
            win = i[1]
            my_team = i[2]
            player_id = i[4]
            tournament_id = i[5]
            elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
            c.execute("""INSERT INTO eloChange(gameId, playerId, tournamentId, eloChange) VALUES (?, ?, ?, ?)""",
                      (game_id, player_id, tournament_id, elo_delta))

        end_of_round = c.execute("""SELECT id FROM games WHERE not games.isBye AND games.tournamentId = ? AND not games.ended""").fetchone()



def create_game(tournamentId, team_one, team_two, official=None, players_one=None, players_two=None, round_number=-1,
                court=0, is_final=False):
    """Pass team_one & team_two in as either int (team id) or str (searchableName)."""
    with DatabaseManager() as c:
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
            print(first_team)
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
            if c.execute("""SELECT id FROM tournamentTeams WHERE teamId = ? AND tournamentId = ?""",
                         (i, tournamentId)).fetchone() is None:
                c.execute(
                    """INSERT INTO tournamentTeams(tournamentId, teamId, gamesWon, gamesPlayed, gamesLost, timeoutsCalled) VALUES (?, ?, 0, 0, 0, 0)""",
                    (
                        tournamentId, i
                    ))
            ranked &= len(c.execute(
                """SELECT people.id FROM people INNER JOIN teams ON (people.id = teams.substitute or people.id = teams.nonCaptain or people.id = teams.captain) WHERE teams.id = ?""",
                (i,)).fetchall()) > 2

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
        if is_bye and first_team == 1:
            first_team, second_team = second_team, first_team

        c.execute("""
            INSERT INTO games(tournamentId, teamOne, teamTwo, official, IGASide, gameStringVersion, gameString, court, isFinal, round, isBye, status, isRanked) 
            VALUES (?, ?, ?, ?, ?, 1, '', ?, ?, ?, ?, 'Waiting For Start', ?)
        """, (tournamentId, first_team, second_team, official, first_team, court, is_final, round_number, is_bye, ranked))
        game_id = c.execute("""SELECT id from games order by id desc limit 1""").fetchone()[0]
        for i, opp in [(first_team, second_team), (second_team, first_team)]:
            players = c.execute(
                """SELECT people.id FROM people INNER JOIN teams ON people.id = teams.captain or people.id = teams.nonCaptain or people.id = teams.substitute WHERE teams.id = ?""",
                (i,)).fetchall()
            for j in players:
                c.execute(
                    """INSERT INTO playerGameStats(gameId, playerId, teamId, opponentId, tournamentId, roundsPlayed, roundsBenched, isBestPlayer, sideOfCourt) VALUES (?, ?, ?, ?, ?, 0, 0, 0, '')""",
                    (game_id, j[0], i, opp, tournamentId))
        return game_id


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
