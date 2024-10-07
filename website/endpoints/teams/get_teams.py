from flask import request

from database.models import Teams, Tournaments, People, TournamentTeams


def add_get_teams_endpoints(app):
    @app.route('/api/team', methods=['GET'])
    def get_teams():
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament the games are from
            player: List<str> (OPTIONAL) = the searchable name of the player who played in the game
        }
        """
        tournament_searchable = request.args.get('tournament', None, type=str)
        player_searchable = request.args.getlist('player', type=str)
        q = Teams.query.filter(Teams.id != 1)
        if tournament_searchable:
            tid = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first().id
            q = q.join(TournamentTeams, TournamentTeams.team_id == Teams.id).filter(
                TournamentTeams.tournament_id == tid)
        for i in player_searchable:
            pid = People.query.filter(People.searchable_name == i).first().id
            q = q.filter((Teams.captain_id == pid) | (Teams.non_captain_id == pid) | (Teams.substitute_id == pid))
        return [i.as_dict() for i in q.all()]

    @app.route('/api/team/<searchable>', methods=['GET'])
    def get_team(searchable):
        """
        SCHEMA:
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament to pull statistics from
        }
        """
        tournament = request.args.get("tournament", None)
        tid = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id if tournament else None
        return Teams.query.filter(Teams.searchable_name == searchable).first().as_dict(include_stats=True,
                                                                                       tournament=tid)
