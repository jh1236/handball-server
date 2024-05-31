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
        "n": "End Timeout"
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


def _add_to_game(game_id, c, char: str, first_team, left_player, team_to_serve=None, details=None, notes=None,
                 add_to_string=True):
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

    c.execute("""INSERT INTO gameEvents(gameId, teamId, playerId, tournamentId, eventType, time, details, notes, playerWhoServed, teamWhoServed, sideServed, nextPlayerToServe, nextTeamToServe, nextServeSide)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?)""", (
        game_id, team if team is not None else None, player if left_player is not None else None, tournament,
        game_string_lookup(char), time.time(),
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
        _add_to_game(game_id, c, "s", first_team, left_player, add_to_string=left_player is not None)
        _next_point(game_id, c)


def ace(game_id):
    with DatabaseManager() as c:
        first_team = bool(
            c.execute("""SELECT servingTeam = teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone())
        left_player = bool(c.execute(
            """SELECT servingTeam = 'Left' FROM games INNER JOIN playerGameStats ON games.playerToServe = playerGameStats.id and games.id = playerGameStats.gameId WHERE games.id = ?""",
            (game_id,)).fetchone())
        _add_to_game(game_id, c, "a", first_team, left_player)
        _next_point(game_id, c)


def fault(game_id):
    with DatabaseManager() as c:
        first_team = bool(
            c.execute("""SELECT servingTeam = teamToServe FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0])
        left_player = bool(c.execute(
            """SELECT servingTeam = 'Left' FROM games INNER JOIN playerGameStats ON games.playerToServe = playerGameStats.id and games.id = playerGameStats.gameId WHERE games.id = ?""",
            (game_id,)).fetchone()[0])
        prev_event = c.execute(
            """SELECT eventType FROM gameEvents WHERE gameId = ? ORDER BY id DESC LIMIT 1""").fetchone()
        if prev_event:
            prev_event = prev_event[0]
        if prev_event == "Fault":
            score_point(game_id, not first_team, None)
        _add_to_game(game_id, c, "f", first_team, left_player)


def card(game_id, first_team, left_player, color, duration, reason):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, color[0], first_team, left_player, notes=reason, details=duration)
        while not c.execute(
                """SELECT id FROM playerGameStats WHERE gameId = ? and teamId = ? and cardTimeRemaining <> 0""").fetchone() or \
                c.execute("""SELECT finished FROM games WHERE id = ?""", (game_id,)).fetchone()[0]:
            score_point(game_id, not first_team, None)


def undo(game_id):
    with DatabaseManager() as c:
        while \
                c.execute("""SELECT notes FROM gameEvents WHERE gameId = ? ORDER BY id DESC LIMIT 1""",
                          (game_id,)).fetchone()[
                    0] == "Penalty":
            c.execute("""DELETE FROM gameEvents 
                     WHERE 
                       gameEvents.ID IN ( 
                          SELECT t.ID 
                          FROM 
                             gameEvents t
                          WHERE t.gameId = ? 
                          ORDER BY 
                             t.id DESC
                          LIMIT 1
                        )""", (game_id,))

        c.execute("""DELETE FROM gameEvents 
                     WHERE 
                       gameEvents.ID IN ( 
                          SELECT t.ID 
                          FROM 
                             gameEvents t
                          WHERE t.gameId = ? 
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
        _add_to_game(game_id, c, 't', first_team, None)


def forfeit(game_id, first_team):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, 'e', first_team, None)


def end_timeout(game_id):
    with DatabaseManager() as c:
        _add_to_game(game_id, c, 'n', None, None, add_to_string=False)


def end_game(game_id, bestPlayer, notes):
    with DatabaseManager() as c:
        if bestPlayer is None:
            allowed = c.execute("""SELECT SUM(eventType = 'Forfeit') > 0 FROM gameEvents WHERE gameId = ?""",(game_id,)).fetchone()[0]
            allowed |= c.execute("""SELECT COUNT(DISTINCT playerID) < 2 FROM playerGameStats WHERE gameId = ? GROUP BY teamId""",(game_id,)).fetchone()[0]
            if not allowed:
                raise ValueError("Best Player was not provided")
        best = c.execute("""SELECT id FROM people WHERE searchableName = ?""", (bestPlayer,)).fetchone()
        if best:
            best = best[0]
        _add_to_game(game_id, c, 'o', None, None, notes=notes, details=best, add_to_string=False)

def create_game(tournamentId, teamOne, teamTwo, official):
    with DatabaseManager() as c:
        if isinstance(teamOne, list):
            players = []
            for i in teamOne:
                players.append(c.execute("""SELECT id FROM people WHERE people.searchableName = ?""", (i,)).fetchone()[0])

            team_one = None
            while not team_one:
                temp = c.execute("""SELECT id FROM teams WHERE captain = """)
                if temp:
                    team_one = temp[0]
        else:
            team_one = c.execute("""SELECT id FROM teams WHERE searchableName = ?""", (teamOne,)).fetchone()[0]


        official = [
            i
            for i in tournament.officials
            if request.json["official"] in [i.nice_name(), i.name]
        ][0]



        if official:
            g.set_primary_official(official)


        last_game = next(i for i in reversed(tournament.games_to_list()) if not i.bye)
        if (
                time.time()
                - last_game.start_time
                > 32400 and len([i for i in tournament.fixtures[-1] if not i.bye])
        ):
            print(tournament.fixtures)
            tournament.update_games(True)
        tournament.update_games()
        tournament.fixtures[-1][-1] = g
        tournament.save()