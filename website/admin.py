import json

from flask import request, render_template

from structure.AllTournament import get_all_games
from structure.GameUtils import game_string_to_commentary
from structure.Player import Player
from structure.Team import Team
from structure.Tournament import Tournament
from utils.util import fixture_sorter
from website.website import sign

from utils.permissions import admin_only, fetch_user
def add_admin_pages(app, comps: dict[str, Tournament]):
    @app.get("/<tournament>/fixtures/admin")
    @admin_only
    def admin_fixtures(tournament):
        court = request.args.get("court", None, type=int)
        round = request.args.get("round", None, type=int)
        umpire = request.args.get("umpire", None, type=str)
        team = request.args.get("team", None, type=str)
        player = request.args.get("player", None, type=str)
        fixtures = comps[tournament].fixtures
        finals = comps[tournament].finals
        fixtures = fixture_sorter(fixtures)
        if court is not None:
            fixtures = [[j for j in i if j.court == court] for i in fixtures]
            finals = [[j for j in i if j.court == court] for i in finals]
        if round is not None:
            fixtures = [[j for j in i if j.round_number == round] for i in fixtures]
            finals = [
                [
                    j
                    for j in i
                    if j.round_number + len(comps[tournament].fixtures) == round
                ]
                for i in finals
            ]
        if umpire is not None:
            fixtures = [
                [
                    j
                    for j in i
                    if umpire in [j.primary_official.nice_name(), j.scorer.nice_name()]
                ]
                for i in fixtures
            ]
            finals = [
                [
                    j
                    for j in i
                    if umpire in [j.primary_official.nice_name(), j.scorer.nice_name()]
                ]
                for i in finals
            ]
        if team is not None:
            fixtures = [
                [j for j in i if team in [k.nice_name() for k in j.teams]]
                for i in fixtures
            ]
            finals = [
                [j for j in i if team in [k.nice_name() for k in j.teams]]
                for i in finals
            ]
        if player is not None:
            fixtures = [
                [j for j in i if player in [k.nice_name() for k in j.players()]]
                for i in fixtures
            ]
            finals = [
                [j for j in i if player in [k.nice_name() for k in j.players()]]
                for i in finals
            ]
        fixtures = [
            (n, [i for i in j if not i.bye or i.best_player])
            for n, j in enumerate(fixtures)
        ]
        finals = [
            (n, [i for i in j if not i.bye or i.best_player])
            for n, j in enumerate(finals)
        ]
        fixtures = [i for i in fixtures if i[1]]
        finals = [i for i in finals if i[1]]
        return (
            render_template(
                "tournament_specific/admin/site.html",
                fixtures=fixtures,
                finals=finals,
                tournament=f"{tournament}/",
                t=comps[tournament],
                reset=court is not None
                or round is not None
                or umpire is not None
                or team is not None
                or player is not None,
            ),
            200,
        )

    @app.get("/signup/admin")
    @admin_only
    def admin_sign_up():
        teams = []
        with open("./config/signups/teams.json") as fp:
            teams_raw = json.load(fp)
        for k, v in teams_raw.items():
            t = Team(k, [Player(j) for j in v["players"]])
            t.primary_color = v["colors"][0]
            t.secondary_color = v["colors"][1]
            teams.append(t)
        with open("config/signups/officials.json") as fp:
            umpires = json.load(fp)
        return render_template(
            "sign_up/admin.html",
            tournament="Fifth S.U.S.S. Championship",
            teams=teams,
            umpires=umpires,
        )

    @app.get("/<tournament>/games/<game_id>/admin")
    @admin_only
    def admin_game_site(tournament, game_id):
        if int(game_id) >= len(comps[tournament].games_to_list()):
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game Does not exist",
                ),
                400,
            )
        game = comps[tournament].get_game(int(game_id))
        teams = game.teams
        team_dicts = [i.get_stats() for i in teams]
        stats = [(i, *[j[i] for j in team_dicts]) for i in team_dicts[0]]
        best = game.best_player.tidy_name() if game.best_player else "TBD"
        players = game.players()
        round_number = game.round_number + 1
        prev_matches = []
        for i in get_all_games():
            if not all(
                [
                    k.nice_name() in [j.team.nice_name() for j in i.teams]
                    for k in game.teams
                ]
            ):
                continue
            if not all(
                [
                    j.team.nice_name() in [k.nice_name() for k in game.teams]
                    for j in i.teams
                ]
            ):
                continue
            if (
                i.tournament.nice_name() == game.tournament.nice_name()
                and i.id == game.id
            ):
                continue
            prev_matches.append(
                (
                    i.full_name,
                    i.id,
                    i.tournament,
                )
            )
        prev_matches = prev_matches or [("No other matches", -1, game.tournament)]
        if not game.started:
            status = "Waiting for toss"
        elif game.in_timeout():
            status = "In Timeout"
        elif not game.game_ended():
            status = "Game in Progress"
        elif not game.best_player:
            status = "Finished"
        else:
            status = "Official"
        player_stats = [
            (i, *[j.get_stats()[i] for j in players]) for i in players[0].get_stats()
        ]
        return (
            render_template(
                "tournament_specific/admin/game_page.html",
                game=game,
                status=status,
                players=[i.tidy_name() for i in players],
                teams=teams,
                stats=stats,
                player_stats=player_stats,
                official=game.primary_official,
                commentary=game_string_to_commentary(game),
                best=best,
                roundNumber=round_number,
                prev_matches=prev_matches,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/teams/<team_name>/admin")
    @admin_only
    def admin_team_site(tournament, team_name):
        team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
        recent_games = []
        key_matches = []
        for i in comps[tournament].games_to_list():
            if team not in [j.team for j in i.teams] or i.bye:
                continue
            if i.started:
                gt = next(j for j in i.teams if j.nice_name() == team_name)
                s = " <+0>"
                if gt.elo_delta:
                    s = f" <{sign(gt.elo_delta)}{round(abs(gt.elo_delta), 2)}>"
                recent_games.append(
                    (
                        repr(i) + f" ({i.score_string()}){s}",
                        i.id,
                        i.tournament.nice_name(),
                    )
                )
                if i.is_noteable or gt.yellow_cards:
                    key_matches.append(
                        (
                            i.noteable_string(True),
                            repr(i) + f" ({i.score_string()}){s}",
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )

        players = [
            (i.name, i.nice_name(), [(k, v) for k, v in i.get_stats().items()])
            for i in team.players
        ]
        return (
            render_template(
                "tournament_specific/admin/each_team_stats.html",
                stats=[(k, v) for k, v in team.get_stats().items()],
                team=team,
                recent_games=recent_games,
                key_games=key_matches,
                tournament=f"{tournament}/",
                players=players,
                ),
            200,
        )


    @app.get("/<tournament>/teams/admin")
    @admin_only
    def admin_stats_directory_site(tournament):
        teams = [
            i
            for i in sorted(comps[tournament].teams, key=lambda a: a.nice_name())
            if i.games_played > 0 or len(comps[tournament].teams) < 15
        ]
        return (
            render_template(
                "tournament_specific/admin/stats.html",
                teams=teams,
                tournament=f"{tournament}/",
                ),
            200,
        )

    @app.get("/<tournament>/players/admin")
    @admin_only
    def admin_players_site(tournament):
        priority = {
            "Name": 1,
            "B&F Votes": 1,
            "Elo": 2,
            "Points scored": 2,
            "Aces scored": 2,
            "Faults": 5,
            "Double Faults": 5,
            "Green Cards": 4,
            "Yellow Cards": 3,
            "Red Cards": 3,
            "Rounds on Court": 5,
            "Points served": 5,
            "Rounds Carded": 5,
            "Games Played": 5,
            "Games Won": 4,
        }
        players = [
            (
                i.name,
                i.team.nice_name(),
                i.nice_name(),
                [(v, priority[k]) for k, v in i.get_stats().items()],
            )
            for i in comps[tournament].players()
            if (i.played or len(comps[tournament].fixtures) < 2)
            and not i.nice_name().startswith("null")
        ]
        headers = ["Name"] + [
            i for i in comps[tournament].teams[0].players[0].get_stats()
        ]
        return (
            render_template(
                "tournament_specific/admin/players.html",
                headers=[(i - 1, k, priority[k]) for i, k in enumerate(headers)],
                players=sorted(players),
                tournament=f"{tournament}/",
                ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/admin")
    @admin_only
    def admin_player_stats(tournament, player_name):
        if player_name not in [i.nice_name() for i in comps[tournament].players()]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        player = [
            i for i in comps[tournament].players() if player_name == i.nice_name()
        ][0]
        noteable_games = []
        cards = []
        for i in comps[tournament].games_to_list():
            if player_name not in [j.nice_name() for j in i.players()] or i.bye:
                continue
            gt = next(
                t for t in i.teams if player_name in [j.nice_name() for j in t.players]
            )
            gp = next(p for p in gt.players if player_name == p.nice_name())
            op = next(k for k in i.teams if k.nice_name() != gt.nice_name())
            s = " <+0>"
            if gt.elo_delta:
                s = f" <{sign(gp.elo_delta)}{round(abs(gp.elo_delta), 2)}>"
            if i.started:
                for j in i.cards:
                    if j.player.nice_name() == player_name:
                        cards.append((op, i.id, j.color, j.reason.title()))
                if (
                    gp.yellow_cards
                    or gp.red_cards
                    or i.notes.strip()
                    or (
                        i.protested
                        and i.teams[i.protested - 1].nice_name() == gt.nice_name()
                    )
                ):
                    noteable_games.append(
                        (
                            i.noteable_string(True),
                            repr(i) + f" ({i.score_string()}){s}",
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )

        return (
            render_template(
                "tournament_specific/admin/player_stats.html",
                stats=[(k, v) for k, v in player.get_stats_detailed().items()],
                name=player.name,
                player=player,
                cards=cards,
                noteable_games=noteable_games,
                tournament=f"{tournament}/",
                ),
            200,
        )

    @app.get("/<tournament>/admin")
    @admin_only
    def admin_home_page(tournament):
        in_progress = any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        )
        games_requiring_action = []
        for i in comps[tournament].games_to_list():
            if i.requires_action:
                games_requiring_action.append(i)
        ongoing_games = [
            i for i in comps[tournament].games_to_list() if i.in_progress()
        ]
        current_round = fixture_sorter(
            [
                [
                    game
                    for r in comps[tournament].finals
                    for game in r
                    if not game.super_bye
                ]
                if comps[tournament].in_finals
                else comps[tournament].fixtures[-1]
            ]
        )[0]
        if (
            all([i.bye for i in current_round]) and len(comps[tournament].fixtures) > 1
        ):  # basically just for home and aways
            current_round = comps[tournament].fixtures[-2]
        players = comps[tournament].players()
        players = [i for i in players if "null" not in i.nice_name()]
        players.sort(key=lambda a: -a.total_cards())
        if len(players) > 10:
            players = players[0:10]

        return (
            render_template(
                "tournament_specific/admin/tournament_home.html",
                tourney=comps[tournament],
                ongoing=ongoing_games,
                current_round=current_round,
                players=players,
                notes=comps[tournament].notes,
                in_progress=in_progress,
                tournament=f"{tournament}/",
                require_action=games_requiring_action,
            ),
            200,
        )
