from flask import request

from database.models import PlayerGameStats, Teams, Tournaments, People


def add_get_player_endpoints(app):
    @app.get("/api/player")
    def get_players():
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament the games are from
            team: str (OPTIONAL) = the searchable name of the team the player played with
        }
        """
        tournament = request.args.get("tournament", None)
        team = request.args.get("team", None)
        q = PlayerGameStats.query
        if tournament:
            tid = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id
            q = q.filter(PlayerGameStats.tournament_id == tid)
        if team:
            tid = Teams.query.filter(Teams.searchable_name == team).first().id
            q = q.filter(PlayerGameStats.team_id == tid)
        q = q.group_by(PlayerGameStats.player_id)
        return [i.player.as_dict() for i in q.all()]

    @app.get("/api/player/<searchable>")
    def get_player(searchable):
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament to pull statistics from
            game: <int> (OPTIONAL) = the game to get the stats for this player
        }
        """
        game = request.args.get("game", None, type=int)
        if game:
            return PlayerGameStats.query.join(People, PlayerGameStats.player_id == People.id).filter(
                PlayerGameStats.game_id == game, People.searchable_name == searchable).first().as_dict()
        tournament = request.args.get("tournament", None)
        tid = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id if tournament else None
        return People.query.filter(People.searchable_name == searchable).first().as_dict(include_stats=True,
                                                                                         tournament=tid)
