from flask import request

from database.models import PlayerGameStats, Teams, Tournaments, People


def add_get_player_endpoints(app):
    @app.get("/api/players")
    def get_players():
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament the games are from
            team: <str> (OPTIONAL) = the searchable name of the team the player played with
            includeStats: <bool> (OPTIONAL) = whether stats should be included
        }
        """
        tournament_searchable = request.args.get("tournament", None)
        team = request.args.get("team", None)
        make_nice = request.args.get('formatData', False, type=bool)
        return_tournament = request.args.get('returnTournament', False, type=bool)
        include_stats = request.args.get("includeStats", False, type=bool)
        q = PlayerGameStats.query
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()
        if tournament_searchable:
            tid = tournament.id
            q = q.filter(PlayerGameStats.tournament_id == tid)
        if team:
            tid = Teams.query.filter(Teams.searchable_name == team).first().id
            q = q.filter(PlayerGameStats.team_id == tid)
        q = q.group_by(PlayerGameStats.player_id)
        out = {"players": [i.player.as_dict(include_stats=include_stats, make_nice=make_nice, tournament=tournament.id if tournament else None) for i in q.all()]}
        if return_tournament and tournament_searchable:
            out["tournament"] = tournament.as_dict()
        return out

    @app.get("/api/players/<searchable>")
    def get_player(searchable):
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament to pull statistics from
            game: <int> (OPTIONAL) = the game to get the stats for this player
        }
        """
        make_nice = request.args.get('formatData', False, type=bool)
        return_tournament = request.args.get('returnTournament', False, type=bool)
        game = request.args.get("game", None, type=int)
        if game:
            return PlayerGameStats.query.join(People, PlayerGameStats.player_id == People.id).filter(
                PlayerGameStats.game_id == game, People.searchable_name == searchable).first().as_dict()
        tournament_searchable = request.args.get("tournament", None)
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()
        tid = tournament.id if tournament else None
        out = {"player": People.query.filter(People.searchable_name == searchable).first().as_dict(include_stats=True,
                                                                                                   tournament=tid,
                                                                                                   make_nice=make_nice)}
        if return_tournament and tournament_searchable:
            out["tournament"] = tournament.as_dict()
        return out
