import time

from utils.databaseManager import DatabaseManager

SIDES = ["Left", "Right", "Substitute"]


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
        "e": "Forfeit",
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
                INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND games.servingTeam = playerGameStats.teamId
            WHERE teamId = sideOfCourt = ? and gameId = ?""",
                           SIDES[not left_player], game_id).fetchone()[0]
    else:
        player = c.execute("""
            SELECT playerId
            FROM games
                INNER JOIN playerGameStats ON games.id = playerGameStats.gameId AND games.receivingTeam = playerGameStats.teamId
            WHERE teamId = sideOfCourt = ? and gameId = ?""",
                           SIDES[not left_player], game_id).fetchone()[0]
    return player


def _team_to_id(game_id, first_team, c) -> int:
    if first_team:
        team = c.execute("""SELECT servingTeam FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
    else:
        team = c.execute("""SELECT servingTeam FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
    return team


def _next_point(game_id, c):
    c.execute(
        """UPDATE playerGameStats SET roundsPlayed = roundsPlayed + 1 WHERE cardTimeRemaining = 0 and gameId = ?""",
        (game_id,))
    c.execute(
        """UPDATE playerGameStats SET roundsBenched = roundsBenched + 1 WHERE cardTimeRemaining <> 0 and gameId = ?""",
        (game_id,))
    c.execute(
        """UPDATE playerGameStats SET cardTimeRemaining = cardTimeRemaining - 1 WHERE cardTimeRemaining > 0 and gameId = ?""",
        (game_id,))


def _tournament_from_game(game_id, c):
    return c.execute("""SELECT tournamentId FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]


def _swap_server(game_id, team_to_serve, c):
    old_side = c.execute(
        """SELECT sideServed FROM gameEvents WHERE gameId = ? AND teamId = ? ORDER BY id DESC  LIMIT 1""",
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
        """SELECT playerId FROM playerGameStats WHERE gameId = ? AND teamId = ? AND cardTimeRemaining = 0 ORDER BY sideOfCourt = ?  LIMIT 1""",
        (game_id, team_to_serve, new_side)).fetchone()
    return player_to_serve, new_side


def _get_serve_details(game_id, c):
    return tuple(c.execute(
        """SELECT teamWhoServed, playerWhoServed, sideServed from gameEvents WHERE gameId = ? order by id DESC LIMIT 1""",
        (game_id,)).fetchone())


def _add_to_game(game_id, c, char: str, first_team, left_player, team_to_serve=None, details=None, notes=None, add_to_string = True):
    if left_player is not None:
        string = char + "L" if left_player else "R"
    else:
        string = char * 2
    string = string.upper() if first_team else string.lower()
    if add_to_string:
        c.execute("""UPDATE gamesTable SET gameString = gameString + ? WHERE gamesTable.id = ?""", (string, game_id))
    player = _team_and_position_to_id(game_id, first_team, left_player, c)
    team = _team_to_id(game_id, first_team, c)
    tournament = _tournament_from_game(game_id, c)
    team_who_served, player_who_served, serve_side = _get_serve_details(game_id, c)
    if team_to_serve is None or team_who_served == (next_team_to_serve := (_team_to_id(game_id, team_to_serve, c))):
        next_team_to_serve, next_player_to_serve, next_serve_side = team_who_served, player_who_served, serve_side
    else:
        next_player_to_serve, next_serve_side = _swap_server(game_id, next_team_to_serve, c)
    c.execute("""INSERT INTO gameEvents (gameId, playerId, tournamentId, eventType, time) VALUES (?, ?, ?, ?, ?)""",
              (game_id, player if left_player is not None else None, team, tournament, game_string_lookup(char),
               time.time()))

    c.execute("""INSERT INTO gameEvents(gameId, teamId, playerId, tournamentId, eventType, time, details, notes, playerWhoServed, teamWhoServed, sideServed, nextPlayerToServe, nextTeamToServe, nextServeSide)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?)""", (
        game_id, team, player if left_player is not None else None, tournament, game_string_lookup(char), time.time(),
        details, notes,
        player_who_served, team_who_served, serve_side,
        next_team_to_serve, next_player_to_serve, next_serve_side))


def start_game(game_id, swapService, teamOne, teamTwo, teamOneIGA, official=None, scorer=None):
    with DatabaseManager() as c:
        tournament = _tournament_from_game(game_id, c)
        iga = c.execute("""SELECT servingTeam, receivingTeam FROM games WHERE games.id = ?""", (game_id,)).fetchall()[
            1 - teamOneIGA]
        c.execute(
            """UPDATE games SET started = 1, status = adminStatus = 'In Progress', startTime = ?, IGASide = ? where id = ?""",
            (time.time(), iga, game_id,))
        if swapService:
            c.execute("""UPDATE games SET servingTeam = receivingTeam, receivingTeam = servingTeam where id = ?""",
                      (game_id,))
        if official:
            c.execute("""
                UPDATE games SET official = 
                (SELECT officials.id
                 from officials INNER JOIN people where people.searchableName = ?) 
                 where id = ?""", (official, game_id))
        if scorer:
            c.execute("""
                UPDATE games SET scorer = 
                (SELECT officials.id
                 from officials INNER JOIN people where people.searchableName = ?) 
                 where id = ?""", (scorer, game_id))
        for name, side in zip(teamOne, SIDES):
            c.execute("""
                UPDATE playerGameStats SET sideOfCourt = ? 
                where 
                    playerGameStats.id = (SELECT people.id from people where people.searchableName = ?) and
                    playerGameStats.gameId = ?""",
                      (side, name, game_id))
        for name, side in zip(teamTwo, SIDES):
            c.execute("""
                UPDATE playerGameStats SET sideOfCourt = ? 
                where 
                    playerGameStats.id = (SELECT people.id from people where people.searchableName = ?) and
                    playerGameStats.gameId = ?""",
                      (side, name, game_id))

        c.execute("""INSERT INTO gameEvents(gameId, tournamentId, eventType, time, nextPlayerToServe, nextTeamToServe, nextServeSide)
                     SELECT games.id, ?, 'Start', ?, playerGameStats.playerId, servingTeam, 'Left'
                     FROM games
                              INNER JOIN playerGameStats ON playerGameStats.gameId = games.id
                         AND sideOfCourt = 'Left' AND playerGameStats.teamId = games.servingTeam
                     WHERE games.id = ?
         """, (tournament, time.time(), game_id))


def score_point(game_id, first_team, left_player):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, "s", first_team, left_player)
        _next_point(game_id, c)


def ace(game_id):
    with DatabaseManager() as c:
        first_team = bool(
            c.execute("""SELECT servingTeam = teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone())
        left_player = bool(c.execute(
            """SELECT servingTeam = 'Left' FROM games INNER JOIN playerGameStats ON games.playerToServe = playerGameStats.id and games.id = playerGameStats.gameId WHERE games.id = ?""",
            (game_id,)).fetchone())
        c.execute("""
                UPDATE games SET servingTeam = servingTeam + (servingTeam == teamToServe), receivingTeam = receivingTeam + (receivingTeam == teamToServe) WHERE id = ?
            """, (game_id,))
        c.execute("""UPDATE playerGameStats SET points = points + 1, aces = aces + 1 WHERE gameId = ? and playerId = 
                (SELECT playerToServe FROM games WHERE id = ?)""",
                  (game_id, game_id))
        _add_to_game(game_id, c, "a", first_team, left_player)
        _next_point(game_id, c)


def fault(game_id):
    with DatabaseManager() as c:
        first_team = bool(
            c.execute("""SELECT servingTeam = teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone())
        left_player = bool(c.execute(
            """SELECT servingTeam = 'Left' FROM games INNER JOIN playerGameStats ON games.playerToServe = playerGameStats.id and games.id = playerGameStats.gameId WHERE games.id = ?""",
            (game_id,)).fetchone())
        c.execute("""
                UPDATE games SET servingTeam = servingTeam + (servingTeam = teamToServe), receivingTeam = receivingTeam + (receivingTeam= teamToServe) WHERE id = ?
            """, (game_id,))
        c.execute("""UPDATE playerGameStats SET points = points + 1, aces = aces + 1 WHERE gameId = ? and playerId = 
                (SELECT playerToServe FROM games WHERE id = ?)""",
                  (game_id, game_id))
        prev_event = c.execute(
            """SELECT eventType FROM gameEvents WHERE gameId = ? ORDER BY id DESC LIMIT 1""").fetchone()
        if prev_event:
            prev_event = prev_event[0]
        if prev_event == "Fault":
            score_point(game_id, not first_team, None)
        _add_to_game(game_id, c, "f", first_team, left_player)


def card(game_id, first_team, left_player, color, duration, reason):
    with DatabaseManager() as c:
        if first_team:
            if color == "Red":
                c.execute("""UPDATE playerGameStatsTable 
                             SET cardTimeRemaining = -1, cardTime = -1
                                 WHERE gameId = ? and sideOfCourt = ? and teamID = 
                                     (SELECT servingTeam FROM games WHERE id = ?)""",
                                           (duration, duration, game_id, SIDES[not left_player], game_id))
            else:
                c.execute("""UPDATE playerGameStatsTable 
                             SET cardTimeRemaining = cardTimeRemaining + ?,
                              cardTime = cardTimeRemaining + ? WHERE gameId = ? and sideOfCourt = ? and cardTime >= 0 and
                               teamID = (SELECT servingTeam FROM games WHERE id = ?)""",
                                       (duration, duration, game_id, SIDES[not left_player], game_id))
            while not c.execute("""SELECT id from playerGameStats WHERE cardTimeRemaining = 0""").fetchone():
                _add_to_game(game_id, c, 's', False, None, team_to_serve=False, notes="Penalty", )
        else:
            if color == "Red":
                c.execute("""UPDATE playerGameStatsTable 
                             SET cardTimeRemaining = -1, cardTime = -1
                                 WHERE gameId = ? and sideOfCourt = ? and teamID = 
                                     (SELECT receivingTeam FROM games WHERE id = ?)""",
                          (duration, duration, game_id, SIDES[not left_player], game_id))
            else:
                c.execute("""UPDATE playerGameStatsTable 
                             SET cardTimeRemaining = cardTimeRemaining + ?,
                              cardTime = cardTimeRemaining + ? WHERE gameId = ? and sideOfCourt = ? and cardTime >= 0 and
                               teamID = (SELECT receivingTeam FROM games WHERE id = ?)""",
                          (duration, duration, game_id, SIDES[not left_player], game_id))
        _add_to_game(game_id, color[0], "s", first_team, left_player, notes=reason, details=duration)
