from structure.manageGame import game_string_lookup
from utils.util import chunks_sized


def load_from_string(self, game_string: str, s):
    if self.bye:
        return
    game_id = s.execute("SELECT id FROM gamesTable ORDER BY id DESC LIMIT 1").fetchone()[0]
    tournament = s.execute("""SELECT id FROM tournaments WHERE searchableName = ?""",
                           (self.tournament.nice_name(),)).fetchone()[0]
    card_count = 0

    j: str
    [i.reset() for i in self.teams]
    self.rounds = 0
    self.teams[not self.first_team_serves].serving = True
    servingTeam = \
    s.execute("SELECT id FROM teams WHERE searchableName = ?", (self.team_serving.nice_name(),)).fetchone()[0]
    servingPlayer = s.execute("SELECT id FROM people WHERE searchableName = ?", (self.server.nice_name(),)).fetchone()[
        0]
    s.execute(
        """INSERT INTO gameEvents (gameId, playerId, teamId, tournamentId, eventType, time, details, nextPlayerToServe, nextTeamToServe, sideServed, nextServeSide) VALUES (?,?,?,?, 'Start', -1, null, ?, ?, null, 'Left')""",
        (game_id, None, None, tournament, servingPlayer, servingTeam))
    for j in chunks_sized(game_string, 2):
        oldServingTeam = \
        s.execute("SELECT id FROM teams WHERE searchableName = ?", (self.team_serving.nice_name(),)).fetchone()[0]
        oldServingPlayer = \
        s.execute("SELECT id FROM people WHERE searchableName = ?", (self.server.nice_name(),)).fetchone()[0]
        side_served_from = "Left" if self.team_serving.first_player_serves else "Right"
        team = self.teams[not j[1].isupper()]
        first = j[1].upper() == "L"
        c = j[0].lower()
        if c == "s":
            team.score_point(first)
        elif c == "a":
            team.score_point(None, True)
            first = self.server.nice_name() == team.players[0].nice_name()
        elif c == "g":
            team.green_card(first)
        elif c == "y":
            team.yellow_card(first)
        elif c == "v":
            team.red_card(first)
        elif c == "f":
            first = self.server.nice_name() == team.players[0].nice_name()
            team.fault()
        elif c == "t":
            team.timeout()
            team.end_timeout()
        elif c == "x":
            team.sub_player(first)
        elif c == "e":
            team.forfeit()
        elif c == "!":
            c2 = j[1].lower()
            if c2 == "h":
                self.swap_serve()
            elif c2 == "u":
                team.swap_players(True)
            elif c2 == "w":
                self.swap_serve_team()
        elif c.isdigit():
            if int(c) <= 3:
                team.yellow_card(first, int(c) + 10)
            else:
                team.yellow_card(first, int(c))

        team_id = s.execute("""SELECT id FROM teams WHERE searchableName = ?""", (team.nice_name(),)).fetchone()[0]
        player_id = s.execute("""SELECT id FROM people WHERE searchableName = ?""",
                              (team.players[not first].nice_name(),)).fetchone()[0]

        event_type = game_string_lookup(c)
        if not event_type: continue
        details = None
        notes = None
        if event_type.endswith(" Card"):
            if "null" in team.players[not first].nice_name(): continue
            notes = self.cards[card_count].reason
            if event_type == "Yellow Card":
                if c.isdigit():
                    details = int(c) + (10 * int(c) <= 2)
                else:
                    details = 3
            card_count += 1
        elif event_type == "Substitute":
            details = s.execute(
                """SELECT playerId FROM playerGameStats WHERE gameId = ? and sideOfCourt = 'Substitute' and teamId = ?""",
                (game_id, team_id)).fetchone()
            if details: details = details[0]
        servingTeam = \
        s.execute("SELECT id FROM teams WHERE searchableName = ?", (self.team_serving.nice_name(),)).fetchone()[0]
        servingPlayer = \
        s.execute("SELECT id FROM people WHERE searchableName = ?", (self.server.nice_name(),)).fetchone()[0]
        serving_side = "Left" if self.team_serving.first_player_serves else "Right"
        if self.game_ended:
            servingTeam = servingPlayer = serving_side = None
        s.execute(
            """INSERT INTO gameEvents (gameId, playerId, teamId, tournamentId, eventType, time, details, nextPlayerToServe, nextTeamToServe, playerWhoServed, teamWhoServed, sideServed, nextServeSide, notes) VALUES (?,?,?,?,?, -1,?, ?, ?, ?, ?, ?, ?, ?)""",
            (game_id, player_id, team_id, tournament, event_type, details, servingPlayer, servingTeam, oldServingPlayer,
             oldServingTeam, side_served_from, serving_side, notes))
    self.game_string = game_string