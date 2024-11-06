from flask import request

from database.models import PlayerGameStats, Teams, Tournaments, People
from utils.enable_cors import enable_cors


def add_get_player_endpoints(app):
    @app.get("/api/players")
    @enable_cors
    def get_players():
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament the games are from
            team: <str> (OPTIONAL) = the searchable name of the team the player played with
            includeStats: <bool> (OPTIONAL) = whether stats should be included
        }
        """
        tournament = request.args.get("tournament", None)
        team = request.args.get("team", None)
        make_nice = request.args.get('formatData', False, type=bool)

        includeStats = request.args.get("includeStats", False, type=bool)
        q = PlayerGameStats.query
        if tournament:
            tid = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id
            q = q.filter(PlayerGameStats.tournament_id == tid)
        if team:
            tid = Teams.query.filter(Teams.searchable_name == team).first().id
            q = q.filter(PlayerGameStats.team_id == tid)
        q = q.group_by(PlayerGameStats.player_id)
        return [i.player.as_dict(include_stats=includeStats, make_nice=make_nice) for i in q.all()]

    @app.get("/api/players/<searchable>")
    @enable_cors
    def get_player(searchable):
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament to pull statistics from
            game: <int> (OPTIONAL) = the game to get the stats for this player
        }
        """
        make_nice = request.args.get('formatData', False, type=bool)

        game = request.args.get("game", None, type=int)
        if game:
            return PlayerGameStats.query.join(People, PlayerGameStats.player_id == People.id).filter(
                PlayerGameStats.game_id == game, People.searchable_name == searchable).first().as_dict()
        tournament = request.args.get("tournament", None)
        tid = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id if tournament else None
        return People.query.filter(People.searchable_name == searchable).first().as_dict(include_stats=True,
                                                                                         tournament=tid, make_nice=make_nice)

