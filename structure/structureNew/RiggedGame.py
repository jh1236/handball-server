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
        penalty_count = 0
        penalty_team = None
        penalty_player = None
        oldServingTeam = \
            s.execute("SELECT id FROM teams WHERE searchableName = ?", (self.team_serving.nice_name(),)).fetchone()[0]
        oldServingPlayer = \
            s.execute("SELECT id FROM people WHERE searchableName = ?", (self.server.nice_name(),)).fetchone()[0]
        side_served_from = "Left" if self.team_serving.first_player_serves else "Right"
        team = self.teams[not j[1].isupper()]
        first = j[1].upper() == "L"
        c = j[0].lower()
        other_score = self.teams[j[1].isupper()].score
        if c == "s":
            team.score_point(first)
        elif c == "a":
            team.score_point(None, True)
            first = self.server.nice_name() == team.players[0].nice_name()
            penalty_team = self.team_serving
            penalty_count = 1
            penalty_player = penalty_team.players[first]
        elif c == "g":
            team.green_card(first)
        elif c == "y":
            team.yellow_card(first)
            penalty_team = self.teams[j[1].isupper()]
            penalty_count = self.teams[j[1].isupper()].score - other_score
        elif c == "v":
            team.red_card(first)
            penalty_team = self.teams[j[1].isupper()]
            penalty_count = self.teams[j[1].isupper()].score - other_score
        elif c == "f":
            first = self.server.nice_name() == team.players[0].nice_name()
            team.fault()
            penalty_team = self.team_serving
            penalty_count = 1 - self.team_serving.faulted
        elif c == "t":
            first = None
            team.timeout()
            team.end_timeout()
        elif c == "x":
            team.sub_player(first)
        elif c == "e":
            team.forfeit()
            first = None
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
            penalty_team = self.teams[j[1].isupper()]
            penalty_count = self.teams[j[1].isupper()].score - other_score

        team_id = s.execute("""SELECT id FROM teams WHERE searchableName = ?""", (team.nice_name(),)).fetchone()[0]
        if first is None:
            player_id = None
        else:
            player_id = s.execute("""SELECT id FROM people WHERE searchableName = ?""",
                                  (team.players[not first].nice_name(),)).fetchone()[0]

        event_type = game_string_lookup(c)
        if not event_type: continue
        details = None
        notes = None
        servingTeam = \
            s.execute("SELECT id FROM teams WHERE searchableName = ?", (self.team_serving.nice_name(),)).fetchone()[0]
        servingPlayer = \
            s.execute("SELECT id FROM people WHERE searchableName = ?", (self.server.nice_name(),)).fetchone()[0]
        serving_side = "Left" if self.team_serving.first_player_serves else "Right"
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

        if self.game_ended:
            servingTeam = servingPlayer = serving_side = None
        s.execute(
            """INSERT INTO gameEvents (gameId, playerId, teamId, tournamentId, eventType, time, details, nextPlayerToServe, nextTeamToServe, playerWhoServed, teamWhoServed, sideServed, nextServeSide, notes) VALUES (?,?,?,?,?, -1,?, ?, ?, ?, ?, ?, ?, ?)""",
            (game_id, player_id, team_id, tournament, event_type, details, servingPlayer, servingTeam, oldServingPlayer,
             oldServingTeam, side_served_from, serving_side, notes))
        if penalty_count > 0:
            team = s.execute("SELECT id FROM teams WHERE searchableName = ?", (penalty_team.nice_name(),)).fetchone()[0]
            if penalty_player:
                penalty_player = \
                s.execute("SELECT id FROM people WHERE searchableName = ?", (penalty_player.nice_name(),)).fetchone()[0]
            for i in range(penalty_count):
                s.execute(
                    """INSERT INTO gameEvents (gameId, teamId, playerId, tournamentId, eventType, time, nextPlayerToServe, nextTeamToServe, playerWhoServed, teamWhoServed, sideServed, nextServeSide, notes) VALUES (?,?,?,?,'Score', -1,?, ?, ?, ?, ?, ?, 'Penalty')""",
                    (game_id, team, penalty_player, tournament, servingPlayer, servingTeam, oldServingPlayer,
                     oldServingTeam, side_served_from, serving_side))
    details = s.execute(
        """SELECT id FROM people WHERE searchableName = ?""",
        (self.best_player.nice_name(),)).fetchone()
    if details:
        details = details[0]
    if self.protested:
        if self.protested == 3:
            for i in self.teams:
                team = s.execute("SELECT id FROM teams WHERE searchableName = ?", (i.nice_name(),)).fetchone()[0]
                s.execute(
                    """INSERT INTO gameEvents (gameId, teamId,  tournamentId, eventType, time, details, notes) VALUES (?, ?, ?, 'Protest', -1, ?, ?)""",
                    (game_id, team, tournament, details, self.notes))
        else:
            team = s.execute("SELECT id FROM teams WHERE searchableName = ?", (self.teams[self.protested - 1].nice_name(),)).fetchone()[0]
            s.execute(
                """INSERT INTO gameEvents (gameId, teamId,  tournamentId, eventType, time, details, notes) VALUES (?, ?, ?, 'Protest', -1, ?, ?)""",
                (game_id, team, tournament, details, self.notes))

    s.execute(
        """INSERT INTO gameEvents (gameId,  tournamentId, eventType, time, notes) VALUES (?, ?,'End Game', -1, ?)""",
        (game_id, tournament, self.notes))
    if self.resolved:
        s.execute(
            """INSERT INTO gameEvents (gameId,  tournamentId, eventType, time) VALUES (?, ?,'Resolve', -1)""",
            (game_id, tournament))