from collections import defaultdict

from flask import request

from database.models import Games, Tournaments, Teams, PlayerGameStats, People, Officials
from utils.permissions import fetch_user
from utils.util import fixture_sorter


def add_get_game_endpoints(app):
    @app.route('/api/games/<int:id>', methods=['GET'])
    def get_game(id):
        """
        SCHEMA :
        {
            id: <int> = the id of the game
            includeGameEvents: <bool> (OPTIONAL) = whether gameEvents should be included
            includePlayerStats: <bool> (OPTIONAL) = whether Player Stats should be included
        }
        """
        game = Games.query.filter(Games.id == id).first()
        include_game_events = request.args.get('includeGameEvents', None, type=bool)
        include_player_stats = request.args.get('includePlayerStats', False, type=bool)
        out = {
            "game": game.as_dict(include_game_events=include_game_events, include_player_stats=include_player_stats)
        }
        return out

    @app.route('/api/games', methods=['GET'])
    def get_games():
        """
        SCHEMA :
        {
            tournament: <str> (OPTIONAL) = the searchable name of the tournament the games are from
            team: List<str> (OPTIONAL) = the searchable name of the team who played in the game
            player: List<str> (OPTIONAL) = the searchable name of the player who played in the game
            official: List<str> (OPTIONAL) = the searchable name of the officials who officiated in the game
            court: <str> (OPTIONAL) = the court the game was on
            includeGameEvents: <bool> (OPTIONAL) = whether Game Events should be included
            includePlayerStats: <bool> (OPTIONAL) = whether Player Stats should be included
        }
        """
        is_admin = fetch_user().is_admin
        tournament_searchable = request.args.get('tournament', None, type=str)
        team_searchable = request.args.getlist('team', type=str)
        player_searchable = request.args.getlist('player', type=str)
        official_searchable = request.args.getlist('official', type=str)
        court = request.args.get('court', None, type=int)
        include_game_events = request.args.get('includeGameEvents', False, type=bool) and is_admin
        include_player_stats = request.args.get('includePlayerStats', False, type=bool) and is_admin
        return_tournament = request.args.get('returnTournament', False, type=bool)
        games = Games.query
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()
        if tournament_searchable:
            tid = tournament.id
            games = games.filter(Games.tournament_id == tid)
        for i in official_searchable:
            off_id = Officials.query.join(People, Officials.person_id == People.id).filter(
                People.searchable_name == i).first().id
            games = games.filter((Games.official_id == off_id) | (Games.scorer_id == off_id))
        for i in team_searchable:
            team_id = Teams.query.filter(Teams.searchable_name == i).first().id
            games = games.filter((Games.team_one_id == team_id) | (Games.team_two_id == team_id))
        if court:
            games = games.filter(Games.court == court - 1)
        for i in player_searchable:
            pid = People.query.filter(People.searchable_name == i).first().id
            # this repeated join is a bit cursed, but oh well!
            games = games.join(PlayerGameStats, PlayerGameStats.game_id == Games.id).filter(
                PlayerGameStats.player_id == pid)
        games = games.order_by((Games.start_time.desc()), Games.id.desc())
        out = {"games": [i.as_dict(include_game_events=include_game_events, include_player_stats=include_player_stats,
                                   admin_view=is_admin) for i in games.all()]}
        if return_tournament and tournament_searchable:
            out["tournament"] = tournament.as_dict()
        return out

    @app.route('/api/games/fixtures')
    def get_fixtures():
        """
        SCHEMA :
        {
            tournament: <str> = the searchable name of the tournament
        }
        """
        tournament_searchable = request.args.get('tournament', type=str)
        separate_finals = request.args.get('separateFinals', type=bool)
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()

        tid = tournament.first().id
        return_tournament = request.args.get('returnTournament', False, type=bool)

        fixtures = defaultdict(list)
        games = Games.query.filter(Games.tournament_id == tid).all()
        for game in games:
            fixtures[game.round].append(game)
        new_fixtures = []
        for k, v in fixtures.items():
            new_fixtures.append({"games": [j.as_dict() for j in fixture_sorter(v)], "final": v[0].is_final})
        fixtures = new_fixtures
        if separate_finals:
            finals = [i for i in fixtures if i["final"]]
            fixtures = [i for i in fixtures if not i["final"]]
            out = {"fixtures": fixtures, "finals": finals}
        else:
            out = {"fixtures": fixtures}
        if return_tournament and tournament_searchable:
            out["tournament"] = tournament.as_dict()
        return out
