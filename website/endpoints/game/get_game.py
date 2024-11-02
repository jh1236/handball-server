from collections import defaultdict

from flask import request

from database.models import Games, Tournaments, Teams, PlayerGameStats, People, Officials, GameEvents
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

        return game.as_dict(include_game_events=include_game_events, include_player_stats=include_player_stats)

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
        games = Games.query
        if tournament_searchable:
            tid = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first().id
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
        return [i.as_dict(include_game_events=include_game_events, include_player_stats=include_player_stats,
                          admin_view=is_admin) for i in games.all()]

    @app.route('/api/fixtures')
    def get_fixtures():
        """
        SCHEMA :
        {
            tournament: <str> = the searchable name of the tournament
        }
        """
        tournament_searchable = request.args.get('tournament', type=str)
        tid = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first().id
        games = Games.query.filter(Games.tournament_id == tid).all()

        fixtures = defaultdict(list)
        for game in games:
            fixtures[game.round].append(game)
        new_fixtures = []
        for k, v in fixtures.items():
            new_fixtures.append([j.as_dict() for j in fixture_sorter(v)])
        fixtures = new_fixtures
        return fixtures
