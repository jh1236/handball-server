import time

from utils.databaseManager import DatabaseManager

SIDES = ["Left", "Right", "Substitute"]

cheeky_cache = {}


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


def _team_to_id(game_id, first_team, c) -> int:
    if game_id in cheeky_cache:
        return cheeky_cache[game_id][not first_team]
    if first_team:
        team = c.execute("""SELECT teamOne FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
    else:
        team = c.execute("""SELECT teamTwo FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
    return team


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


def _get_serve_details(game_id, c):
    a = c.execute(
        """SELECT nextTeamToServe,nextPlayerToServe,nextServeSide from gameEvents WHERE gameEvents.gameId = ? order by id DESC LIMIT 1""",
        (game_id,)).fetchone()
    return tuple(a)


def _add_to_game(game_id, c, char: str, first_team, left_player, team_to_serve=None, details=None, notes=None):
    player = _team_and_position_to_id(game_id, first_team, left_player, c)
    team = _team_to_id(game_id, first_team, c)
    next_team_to_serve = _team_to_id(game_id, team_to_serve, c)
    tournament = _tournament_from_game(game_id, c)
    team_who_served, player_who_served, serve_side = _get_serve_details(game_id, c)
    if team_to_serve is None or team_who_served == next_team_to_serve:
        next_team_to_serve, next_player_to_serve, next_serve_side = team_who_served, player_who_served, serve_side
    else:
        next_player_to_serve, next_serve_side = _swap_server(game_id, next_team_to_serve, c)

    c.execute("""INSERT INTO gameEvents(gameId, teamId, playerId, tournamentId, eventType, time, details, notes, teamWhoServed,playerWhoServed,  sideServed, nextTeamToServe, nextPlayerToServe, nextServeSide)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?)""", (
        game_id, team if team is not None else None, player if left_player is not None else None, tournament,
        char, time.time(),
        details, notes,
        team_who_served, player_who_served, serve_side,
        next_team_to_serve, next_player_to_serve, next_serve_side))


def start_game(game_id, swap_service, team_one, team_two, team_one_iga, official=None, scorer=None):
    with DatabaseManager() as c:
        tournament = _tournament_from_game(game_id, c)
        team_one_id, team_two_id = c.execute("""SELECT teamOne, teamTwo FROM games WHERE games.id = ?""",
                                             (game_id,)).fetchone()

        cheeky_cache[game_id] = (team_one_id, team_two_id)

        iga = team_one_id if team_one_iga else team_two_id
        c.execute(
            """UPDATE gamesTable SET status = adminStatus = 'In Progress', startTime = ?, IGASide = ? where id = ?""",
            (time.time(), iga, game_id,))
        if official:
            print(official)
            c.execute("""
                UPDATE gamesTable SET official = 
                (SELECT officials.id
                 from officials INNER JOIN people on personId = people.id where people.searchableName = ?) 
                 where id = ?""", (official, game_id))
        if scorer:
            c.execute("""
                UPDATE gamesTable SET scorer = 
                (SELECT officials.id
                 from officials INNER JOIN people on personId = people.id where people.searchableName = ?) 
                 where id = ?""", (scorer, game_id))
        for name, side in zip(team_one, SIDES):
            c.execute("""
                UPDATE playerGameStatsTable SET sideOfCourt = ? 
                where 
                    playerGameStatsTable.playerId = (SELECT people.id from people where people.searchableName = ?) and
                    playerGameStatsTable.gameId = ?""",
                      (side, name, game_id))
        for name, side in zip(team_two, SIDES):
            c.execute("""
                UPDATE playerGameStatsTable SET sideOfCourt = ? 
                where 
                    playerGameStatsTable.playerId = (SELECT people.id from people where people.searchableName = ?) and
                    playerGameStatsTable.gameId = ?""",
                      (side, name, game_id))
        c.execute("""INSERT INTO gameEvents(gameId, tournamentId, eventType, time, nextPlayerToServe, nextTeamToServe, nextServeSide)
                 SELECT games.id, ?, 'Start', ?, playerGameStats.playerId, playerGameStats.teamId, 'Left'
                 FROM games
                          INNER JOIN playerGameStats ON playerGameStats.gameId = games.id
                     AND sideOfCourt = 'Left' AND (playerGameStats.teamId <> games.teamOne) = ?
                 WHERE games.id = ?
     """, (tournament, time.time(), swap_service, game_id))


def _score_point(game_id, c, first_team, left_player, penalty=False):
    _add_to_game(game_id, c, "Score", first_team, left_player, team_to_serve=first_team,
                 notes="Penalty" if penalty else None)


def score_point(game_id, first_team, left_player):
    with DatabaseManager() as c:
        _score_point(game_id, c, first_team, left_player)


def ace(game_id):
    with DatabaseManager() as c:
        first_team = bool(
            c.execute("""SELECT teamOne == teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0])
        left_player = bool(c.execute(
            """SELECT sideToServe = 'Left' FROM games WHERE games.id = ?""",
            (game_id,)).fetchone()[0])
        _add_to_game(game_id, c, "Ace", first_team, left_player)
        _score_point(game_id, c, first_team, left_player, penalty=True)


def fault(game_id):
    with DatabaseManager() as c:
        first_team = bool(
            c.execute("""SELECT teamOne = teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0])
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
        team = _team_to_id(game_id, first_team, c)
        both_carded = c.execute(
            """SELECT MIN(iif(cardTimeRemaining < 0, 12, cardTimeRemaining)) FROM playerGameStats WHERE playerGameStats.gameId = ? AND playerGameStats.teamId = ?""",
            (game_id, team)).fetchone()[0]
        print(both_carded)
        if both_carded != 0:
            my_score, their_score = c.execute("""SELECT teamOneScore, teamTwoScore FROM games WHERE games.id = ?""",(game_id,)).fetchone()
            if not first_team:
                my_score, their_score = their_score, my_score
            both_carded = min(both_carded, max(11 - their_score, my_score + 2 - their_score))
            for _ in range(both_carded):
                _score_point(game_id, c, not first_team, None, penalty=True)


def undo(game_id):
    with DatabaseManager() as c:
        c.execute("""DELETE FROM gameEvents 
                 WHERE 
                   gameId = ? AND
                   id >= ( 
                      SELECT t.ID
                        FROM
                            gameEvents t
                        WHERE t.gameId = gameEvents.gameId AND (t.notes IS NULL or t.notes <> 'Penalty')
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
                          LIMIT 1""", (game_id,)).fetchone() or (0))[0]


def time_out(game_id, first_team):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, "Timeout", first_team, None)


def forfeit(game_id, first_team):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, "Forfeit", first_team, None)


def end_timeout(game_id):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, "End Timeout", None, None)


def end_game(game_id, bestPlayer, notes):
    with DatabaseManager() as c:
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


def create_game(tournamentId, team_one, team_two, official):
    with DatabaseManager() as c:
        tournamentId = \
            c.execute("""SELECT id FROM tournaments WHERE tournaments.searchableName = ?""",
                      (tournamentId,)).fetchone()[0]
        if isinstance(team_one, list):
            players = [None, None, None]
            for i, v in enumerate(team_one):
                players[i] = c.execute("""SELECT id FROM people WHERE people.searchableName = ?""", (i,)).fetchone()[0]

            team_one = c.execute("""SELECT id FROM teams WHERE (captain = ? or nonCaptain = ? or substitute = ?)
             and (captain = ? or nonCaptain = ? or substitute = ?)
             and (captain = ? or nonCaptain = ? or substitute = ?)""",
                                 (players[0], players[0], players[0], players[1], players[1], players[1], players[2],
                                  players[2], players[2])).fetchone()[0]
        else:
            team_one = c.execute("""SELECT id FROM teams WHERE searchableName = ?""", (team_one,)).fetchone()[0]
        if isinstance(team_two, list):
            players = [None, None, None]
            for i, v in enumerate(team_two):
                players[i] = c.execute("""SELECT id FROM people WHERE people.searchableName = ?""", (i,)).fetchone()[0]

            team_two = c.execute("""SELECT id FROM teams WHERE (captain = ? or nonCaptain = ? or substitute = ?)
             and (captain = ? or nonCaptain = ? or substitute = ?)
             and (captain = ? or nonCaptain = ? or substitute = ?)""",
                                 (players[0], players[0], players[0], players[1], players[1], players[1], players[2],
                                  players[2], players[2])).fetchone()[0]
        else:
            team_two = c.execute("""SELECT id FROM teams WHERE searchableName = ?""", (team_two,)).fetchone()[0]

        official = c.execute(
            """SELECT officials.id FROM officials INNER JOIN people ON personId = people.id WHERE searchableName = ?""",
            (official,)).fetchone()[0]

        last_start = c.execute("""SELECT startTime, round FROM games WHERE tournamentId = ? ORDER BY id DESC LIMIT 1""",
                               (tournamentId,)).fetchone()
        if not last_start:
            last_start, round_number = (-1, 0)
        else:
            last_start, round_number = last_start
        last_start = last_start or 1
        if (
                time.time()
                - last_start
                > 32400
        ):
            round_number = round_number + 1

        c.execute("""
            INSERT INTO gamesTable(tournamentId, teamOne, teamTwo, official, IGASide, gameStringVersion, gameString, court, isFinal, round, isBye, status) 
            VALUES (?, ?, ?, ?, ?, 1, '', 0, 0, ?, 0, 'Waiting For Start')
        """, (tournamentId, team_one, team_two, official, team_one, round_number))
        game_id = c.execute("""SELECT id from gamesTable order by id desc limit 1""").fetchone()[0]
        for i, opp in [(team_one, team_two), (team_two, team_one)]:
            players = c.execute(
                """SELECT people.id FROM people INNER JOIN teams ON people.id = teams.captain or people.id = teams.nonCaptain or people.id = teams.substitute WHERE teams.id = ?""",
                (i,)).fetchall()
            for j in players:
                c.execute(
                    """INSERT INTO playerGameStatsTable(gameId, playerId, teamId, opponentId, tournamentId, roundsPlayed, roundsBenched, isBestPlayer, sideOfCourt) VALUES (?, ?, ?, ?, ?, 0, 0, 0, '')""",
                    (game_id, j[0], i, opp, tournamentId))
        return game_id


def protest(game_id, team_one_protest, team_two_protest):
    if team_one_protest:
        _add_to_game(game_id, c, "End Game", None, None, notes=notes, details=best)
    if team_two_protest:
        _add_to_game(game_id, c, "End Game", None, None, notes=notes, details=best)