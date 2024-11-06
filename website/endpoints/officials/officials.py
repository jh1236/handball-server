from flask import request

from database.models import Tournaments, People, Officials, TournamentOfficials


def add_get_official_endpoints(app):
    @app.get("/api/officials")
    def get_officials():
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament the games are from
        }
        """
        tournament_searchable = request.args.get("tournament", None)
        q = Officials.query
        return_tournament = request.args.get('returnTournament', False, type=bool)
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()

        if tournament_searchable:
            tid = tournament.id
            q = q.join(TournamentOfficials, TournamentOfficials.official_id == Officials.id).filter(
                TournamentOfficials.tournament_id == tid)
        else:
            tid = None

        out = {"officials": [i.as_dict(tournament=tid) for i in q.all()]}
        if return_tournament and tournament_searchable:
            out["tournament"] = tournament.as_dict()
        return out

    @app.get("/api/officials/<searchable>")
    def get_official(searchable):
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament to pull statistics from
        }
        """
        tournament_searchable = request.args.get("tournament", None)
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()
        return_tournament = request.args.get('returnTournament', False, type=bool)
        out = {"official": Officials.query.join(People, People.id == Officials.person_id).filter(
            People.searchable_name == searchable).first().as_dict(tournament=tournament)}
        if return_tournament and tournament_searchable:
            out["tournament"] = tournament.as_dict()
        return out
