from collections import defaultdict
from dataclasses import dataclass

from flask import render_template

from database import db
from database.models import Games, Tournaments, EloChange, PlayerGameStats, GameEvents, Teams, TournamentTeams, People
from structure.GameUtils import game_string_to_events
from structure.get_information import get_tournament_id
from utils.databaseManager import DatabaseManager
from utils.logging_handler import logger
from utils.permissions import admin_only
from utils.sidebar_wrapper import render_template_sidebar
from utils.util import fixture_sorter
from website.tournament_specific import priority_to_classname


def add_admin_pages(app):
    @app.get("/<tournament>/fixtures/admin")
    @admin_only
    def admin_fixtures(tournament):
        tournament_id = get_tournament_id(tournament)
        games = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final == False).all()

        # me when i criticize Jareds code then write this abomination
        fixtures = defaultdict(list)
        for game in games:
            fixtures[game.round].append(game)
            logger.debug(game.official)
        new_fixtures = {}
        for k, v in fixtures.items():
            new_fixtures[k] = [j for j in fixture_sorter(v)]
        fixtures = new_fixtures

        games = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final == True).all()
        # idk something about glass houses?
        finals = defaultdict(list)
        for game in games:
            finals[game.round].append(game)
        return (
            render_template_sidebar(
                "tournament_specific/admin/site.html",
                fixtures=fixtures.items(),
                finals=finals.items(),
                t=Tournaments.query.filter(Tournaments.searchable_name == tournament).first(),
                reset=False  # TODO: see todo above
                # reset=court is not None
                # or round is not None
                # or umpire is not None
                # or team is not None
                # or player is not None,
            ),
            200,
        )

    @app.get("/games/<game_id>/admin")
    @admin_only
    def admin_game_site(game_id):
        game = Games.query.filter(Games.id == game_id).first()

        if not game:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game does not exist",
                ),
                404,
            )

        other_games = db.session.query(Games).filter(
            ((Games.team_one_id == game.team_one_id) & (Games.team_two_id == game.team_two_id))
            | ((Games.team_one_id == game.team_two_id) & (Games.team_two_id == game.team_one_id))
            , Games.tournament_id == game.tournament_id, Games.id != game.id).order_by(Games.id.desc()).limit(20).all()

        player_headers = [
            "Elo",
            "Points Scored",
            "Aces Scored",
            "Faults",
            "Double Faults",
            "Rounds on Court",
            "Rounds Carded",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
        ]

        pgs = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
        # quick and dirty hack
        players = [[i for i in pgs if i.team_id == pgs[0].team_id], [i for i in pgs if i.team_id != pgs[0].team_id]]
        teams = [players[0][0].team, players[1][0].team]  # quicker and dirtier hack
        team_stats: list[dict[str, float | str]] = []

        for i, t in enumerate(players):
            team_stats.append({
                "Elo": 0,
                "Faults": 0,
                "Double Faults": 0,
                "Green Cards": 0,
                "Yellow Cards": 0,
                "Red Cards": 0,
                "Timeouts Remaining": 0,
            })
            p: PlayerGameStats  # god i hate python typing
            for p in t:
                team_stats[i]["Elo"] += p.faults
                team_stats[i]["Green Cards"] += p.green_cards
                team_stats[i]["Yellow Cards"] += p.yellow_cards
                team_stats[i]["Red Cards"] += p.red_cards
                team_stats[i]["Faults"] += p.faults
                team_stats[i]["Double Faults"] += p.double_faults
                team_stats[i]["Elo"] += p.player.elo(last_game=game_id)
            team_stats[i]["Timeouts Remaining"] = 1 - (game.team_two_timeouts if i else game.team_one_timeouts)
            team_stats[i]["Elo"] = round(team_stats[i]["Elo"] / len(t), 2)
            elo_change = EloChange.query.filter(EloChange.player_id == t[0].player_id,
                                                EloChange.game_id == game_id).first()
            if elo_change:
                elo_delta = round(elo_change.elo_delta, 2)
                team_stats[i]["Elo"] = f'{team_stats[i]["Elo"]} [{"+" if elo_delta >= 0 else ""}{elo_delta}]'

        prev_matches = [
            (f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}]", i.id,
             i.tournament.searchable_name) for i in other_games
        ]

        @dataclass
        class Card:
            player: str
            team: int
            type: str
            reason: str
            hex: str

        cards = []

        COLORS = {
            "Warning": "#777777",
            "Green": "#84AA63",
            "Yellow": "#C96500",
            "Red": "#EC4A4A"
        }

        card_events = GameEvents.query.filter(
            (GameEvents.event_type == "Warning") | (GameEvents.event_type.like("% Card")),
            (GameEvents.team_id == game.team_one_id) | (GameEvents.team_id == game.team_two_id),
            GameEvents.game_id == game.id).all()

        for i in card_events:
            card_type = i.event_type.replace(" Card", "")
            c = Card(i.player.name, i.team_id, card_type, i.notes, COLORS[card_type])
            cards.append(c)

        prev_matches = prev_matches or [("No other matches", -1, game.tournament.searchable_name)]
        return (
            render_template_sidebar(
                "tournament_specific/admin/game_page.html",
                game=game,
                teams=teams,
                team_stats=team_stats,
                player_headings=player_headers,
                players=players,
                commentary=game_string_to_events(game.id),
                cards=cards,
                prev_matches=prev_matches,
                tournament=game.tournament.name,
                tournamentLink=game.tournament.searchable_name + "/",
            ),
            200,
        )

    @app.get("/<tournament>/teams/<team_name>/admin")
    @admin_only
    def admin_team_site(tournament, team_name):
        tournament = Tournaments.query.filter(
            Tournaments.searchable_name == tournament).first().id if tournament else None
        team = Teams.query.filter(Teams.searchable_name == team_name).first()
        if not team:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        players = team.players()
        game_filter = (lambda a: a.filter(Games.tournament_id == tournament,
                                          PlayerGameStats.team_id == team.id)) if tournament else lambda a: a.filter(
            PlayerGameStats.team_id == team.id)
        key_games = db.session.query(Games, EloChange).join(PlayerGameStats,
                                                            PlayerGameStats.game_id == Games.id).outerjoin(EloChange,
                                                                                                           EloChange.game_id == Games.id).filter(
            Games.ended, PlayerGameStats.team_id == team.id, EloChange.player_id == PlayerGameStats.player_id,
                         PlayerGameStats.player_id == team.captain_id,
                         Games.admin_status != 'Official')

        if tournament:
            key_games = key_games.filter(Games.tournament_id == tournament)
        key_games = key_games.order_by(Games.id.desc()).limit(20).all()

        key_games = [
            (
                i.noteable_status,
                f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}] <{'' if e and e.elo_delta < 0 else '+'}{round(e.elo_delta, 2) if e else 0}>",
                i.id, i.tournament.searchable_name) for i, e in key_games
        ]

        @dataclass
        class Card:
            player: str
            team: int
            type: str
            reason: str
            hex: str
            game_id: int

        cards = []

        COLORS = {
            "Warning": "#777777",
            "Green": "#84AA63",
            "Yellow": "#C96500",
            "Red": "#EC4A4A"
        }

        card_events = GameEvents.query.filter(
            (GameEvents.event_type == "Warning") | (GameEvents.event_type.like("% Card")),
            (GameEvents.team_id == team.id),
            GameEvents.tournament_id == tournament).all()

        for i in card_events:
            card_type = i.event_type.replace(" Card", "")
            c = Card(i.player.name, i.team_id, card_type, i.notes, COLORS[card_type], i.game_id)
            cards.append(c)
        return (
            render_template_sidebar(
                "tournament_specific/admin/each_team_stats.html",
                team=team,
                cards=cards,
                key_games=key_games,
                players=players,
                game_filter=game_filter,
            ),
            200,
        )

    @app.get("/<tournament>/teams/admin")
    @admin_only
    def admin_stats_directory_site(tournament):
        teams = db.session.query(Teams).join(TournamentTeams)
        if tournament:
            tournament_id = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id
            teams = teams.filter(TournamentTeams.tournament_id == tournament_id)
        teams = teams.group_by(Teams.id).order_by(Teams.searchable_name).all()

        return (
            render_template_sidebar(
                "tournament_specific/admin/stats.html",
                teams=teams,
            ),
            200,
        )

    @app.get("/<tournament_searchable>/players/admin")
    @admin_only
    def admin_players_site(tournament_searchable):
        priority = {
            "Name": 1,
            "B&F Votes": 1,
            "Elo": 1,
            "Points Scored": 2,
            "Aces Scored": 2,
            "Faults": 5,
            "Double Faults": 5,
            "Green Cards": 4,
            "Yellow Cards": 3,
            "Red Cards": 3,
            "Rounds on Court": 5,
            "Points Served": 5,
            "Rounds Carded": 5,
            "Games Played": 5,
            "Games Won": 4,
            "Penalty Points":3,
            "Warnings":4,
        }
        player_headers = [
            "B&F Votes",
            "Elo",
            "Games Won",
            "Games Played",
            "Penalty Points",
            "Warnings",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
            "Rounds on Court",
            "Rounds Carded",
            "Points Served",
        ]

        players = People.query.all()
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()
        game_filter = (lambda a: a.filter(PlayerGameStats.tournament_id == tournament.id)) if tournament else None
        unranked = tournament is not None
        players_in = [(i, i.stats(games_filter=game_filter, include_unranked=unranked, admin=True)) for i in players if
                      i.played_in_tournament(tournament_searchable)]
        players = []
        for i in players_in:
            players.append(
                (i[0].name, i[0].image(tournament), i[0].searchable_name,
                 [(i[1][k], (priority_to_classname(priority[k]))) for k in player_headers]))
        return (
            render_template_sidebar(
                "tournament_specific/admin/players.html",
                headers=[(i - 1, k, priority[k]) for i, k in enumerate(["Name"] + player_headers)],
                players=sorted(players),
            ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/admin")
    @admin_only
    def admin_player_stats(tournament, player_name):
        tournament = Tournaments.query.filter(
            Tournaments.searchable_name == tournament).first().id if tournament else None
        player = People.query.filter(People.searchable_name == player_name).first()
        game_filter = (lambda a: a.filter(PlayerGameStats.tournament_id == tournament)) if tournament else lambda a: a
        stats = player.stats(games_filter=game_filter)
        team = db.session.query(Teams).join(TournamentTeams, TournamentTeams.team_id == Teams.id).filter(
            (Teams.captain_id == player.id) | (Teams.non_captain_id == player.id) | (
                    Teams.substitute_id == player.id))
        if tournament:
            team = team.filter(TournamentTeams.tournament_id == tournament)
        team = team.order_by(Teams.image_url.like("/api/teams/image%").desc(),
                             Teams.id).first()
        courts = [player.stats(games_filter=lambda a: game_filter(a).filter(Games.court == i)) for i in range(2)]

        stats |= {
            f"Court {i + 1}": j for i, j in enumerate(courts)
        }

        key_games = db.session.query(Games, EloChange).join(PlayerGameStats,
                                                            PlayerGameStats.game_id == Games.id).outerjoin(EloChange,
                                                                                                           EloChange.game_id == Games.id).filter(
            Games.ended, PlayerGameStats.player_id == player.id, EloChange.player_id == PlayerGameStats.player_id,
                         (Games.admin_status != 'Official') | (Games.best_player_id == player.id))

        if tournament:
            key_games = key_games.filter(Games.tournament_id == tournament)
        key_games = key_games.order_by(Games.id.desc()).limit(20).all()

        key_games = [
            (
                i.noteable_status if i.noteable_status != "Official" else "Best on ground",
                f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}] <{'' if e and e.elo_delta < 0 else '+'}{round(e.elo_delta, 2) if e else 0}>",
                i.id, i.tournament.searchable_name) for i, e in key_games
        ]

        @dataclass
        class Card:
            player: str
            team: int
            type: str
            reason: str
            hex: str
            game_id: int

        cards = []

        COLORS = {
            "Warning": "#777777",
            "Green": "#84AA63",
            "Yellow": "#C96500",
            "Red": "#EC4A4A"
        }

        card_events = GameEvents.query.filter(
            (GameEvents.event_type == "Warning") | (GameEvents.event_type.like("% Card")),
            (GameEvents.player_id == player.id),
            GameEvents.tournament_id == tournament).all()

        for i in card_events:
            card_type = i.event_type.replace(" Card", "")
            c = Card(i.player.name, i.team_id, card_type, i.notes, COLORS[card_type], i.game_id)
            cards.append(c)

        return (
            render_template_sidebar(
                "tournament_specific/admin/player_stats.html",
                stats=stats,
                player=player,
                team=team,
                cards=cards,
                courts=courts,
                key_games=key_games
            ),
            200,
        )

    @app.get("/<tournament>/admin")
    @admin_only
    def admin_home_page(tournament):
        tournament_id: int = get_tournament_id(tournament)
        if tournament_id is None:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real tournament",
                ),
                400,
            )

        tourney = Tournaments.query.filter(Tournaments.id == tournament_id).first()
        with DatabaseManager() as c:
            # there has to be a reason this is the required syntax but i can't work it out1

            games_requiring_action = Games.query.filter(Games.tournament_id == tournament_id,
                                                        Games.is_bye == False,
                                                        Games.admin_status != 'Official',
                                                        Games.admin_status != 'Resolved',
                                                        Games.admin_status != 'Forfeited',
                                                        Games.admin_status != 'Waiting For Start',
                                                        Games.admin_status != 'In Progress').all()

            last_game = Games.query.filter(Games.tournament_id == tournament_id).order_by(Games.id.desc()).first()
            if last_game.is_final:
                current_round = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final).all()
            else:
                current_round = Games.query.filter(Games.tournament_id == tournament_id,
                                                   Games.round == last_game.round).all()

            players = People.query.filter(PlayerGameStats.tournament_id == tournament_id).all()
            f = lambda a: a.filter(Games.tournament_id == tournament_id)
            players = [(i, i.stats(games_filter=f, admin=True)) for i in players]
            players.sort(key=lambda a: (-a[1]["Penalty Points"], -a[1]["Warnings"], -a[1]["Games Played"]))
            if len(players) > 10:
                players = players[:10]
            notes = (
                    tourney.notes.strip()
                    or "Notices will appear here when posted"
            )

        return (
            render_template_sidebar(
                "tournament_specific/admin/tournament_home.html",
                tourney=tourney,
                current_round=current_round,
                players=players,
                notes=notes,
                require_action=games_requiring_action,
            ),
            200,
        )
