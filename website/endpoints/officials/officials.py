from flask import request

from database.models import PlayerGameStats, Teams, Tournaments, People, Officials, TournamentOfficials


def add_get_official_endpoints(app):
    @app.get("/api/official")
    def get_officials():
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament the games are from
        }
        """
        tournament = request.args.get("tournament", None)
        q = Officials.query
        if tournament:
            tid = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id
            q = q.join(TournamentOfficials, TournamentOfficials.official_id == Officials.id).filter(
                TournamentOfficials.tournament_id == tid)
        return [i.player.as_dict() for i in q.all()]

    @app.get("/api/official/<searchable>")
    def get_official(searchable):
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament to pull statistics from
        }
        """
        tournament = request.args.get("tournament", None)
        tid = Tournaments.query.filter(Tournaments.searchable_name == tournament).first()
        return Officials.query.join(People, People.id == Officials.person_id).filter(
            People.searchable_name == searchable).first().as_dict(tournament=tid)
