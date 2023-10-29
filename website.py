import random

from flask import render_template, send_file, request, Response

from structure.AllTournament import (
    get_all_teams,
    get_all_players,
    get_all_officials,
    get_all_games,
)
from structure.GameUtils import game_string_to_commentary
from structure.Tournament import Tournament
from utils.util import fixture_sorter


def init_api(app, comps: dict[str, Tournament]):
    from api import admin_password

    @app.get("/")
    def root():
        return render_template("all_tournaments.html", comps=comps.values()), 200

    @app.get("/rules/")
    def rules():
        return send_file("./resources/rules.pdf"), 200

    @app.get("/admin/")
    def log():
        key = request.args.get("key", None)
        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif key != admin_password:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        return render_template("admin.html"), 200

    @app.get("/code_of_conduct/")
    def code_of_conduct():
        rand = random.Random()
        if rand.randrange(0, 10):
            return send_file("./resources/code_of_conduct_2.pdf"), 200
        return send_file("./resources/code_of_conduct.pdf"), 200

    @app.get("/favicon.ico/")
    def icon():
        return send_file("static/favicon.ico")

    tournament_specific(app, comps)
    universal_tournament(app, comps)


def tournament_specific(app, comps: dict[str, Tournament]):
    from api import admin_password

    @app.get("/<tournament>/")
    def home_page(tournament):
        in_progress = any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        )
        ladder = sorted(
            comps[tournament].teams,
            key=lambda a: (
                -(a.games_won / (a.games_played or 1)),
                -(a.get_stats()["Point Difference"]),
            ),
        )
        ongoing_games = [
            i for i in comps[tournament].games_to_list() if i.in_progress()
        ]
        current_round = (
            [game for r in comps[tournament].finals for game in r]
            if comps[tournament].in_finals
            else comps[tournament].fixtures[-1]
        )
        if (
            all([i.bye for i in current_round]) and len(comps[tournament].fixtures) > 1
        ):  # basically just for home and aways
            current_round = comps[tournament].fixtures[-2]
        players = comps[tournament].players()
        players.sort(key=lambda a: -a.votes)
        if len(players) > 10:
            players = players[0:10]
        if len(ladder) > 10:
            ladder = ladder[0:10]
        notes = comps[tournament].notes or ["Notices will appear here when posted"]
        return (
            render_template(
                "tournament_home.html",
                tourney=comps[tournament],
                ongoing=ongoing_games,
                current_round=current_round,
                players=players,
                notes=notes,
                in_progress=in_progress,
                tournament=f"{tournament}/",
                ladder=list(enumerate(ladder, start=1)),
            ),
            200,
        )

    @app.get("/<tournament>/fixtures/")
    def fixtures(tournament):
        fixtures = comps[tournament].fixtures
        finals = comps[tournament].finals
        fixtures = [
            (n, [i for i in j if not i.bye or i.best_player])
            for n, j in enumerate(fixture_sorter(fixtures))
        ]
        finals = [
            (n, [i for i in j if not i.bye or i.best_player])
            for n, j in enumerate(finals)
        ]
        fixtures = [i for i in fixtures if i]
        finals = [i for i in finals if i]
        return (
            render_template(
                "tournament_specific/site.html",
                fixtures=fixtures,
                finals=finals,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/fixtures/detailed")
    def detailed_fixtures(tournament):
        court = request.args.get("court", None, type=int)
        fixtures = comps[tournament].fixtures
        finals = comps[tournament].finals
        if court is not None:
            fixtures = [[j for j in i if j.court == court] for i in fixtures]
            finals = [[j for j in i if j.court == court] for i in finals]
        fixtures = [
            (n, [i for i in j if not i.bye or i.best_player])
            for n, j in enumerate(fixture_sorter(fixtures))
        ]
        finals = [
            (n, [i for i in j if not i.bye or i.best_player])
            for n, j in enumerate(finals)
        ]
        fixtures = [i for i in fixtures if i[1]]
        finals = [i for i in finals if i[1]]
        return (
            render_template(
                "tournament_specific/site_detailed.html",
                fixtures=fixtures,
                finals=finals,
                tournament=f"{tournament}/",
                t=comps[tournament],
            ),
            200,
        )

    @app.get("/<tournament>/teams/")
    def stats_directory_site(tournament):
        teams = [
            (i.name, i.nice_name())
            for i in sorted(comps[tournament].teams, key=lambda a: a.nice_name())
        ]
        return (
            render_template(
                "tournament_specific/stats.html",
                teams=teams,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/teams/<team_name>/")
    def stats_site(tournament, team_name):
        if team_name not in [i.nice_name() for i in comps[tournament].teams]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real team",
                ),
                400,
            )
        team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
        recent_games = []
        upcoming_games = []
        for i in comps[tournament].games_to_list():
            if team not in [j.team for j in i.teams] or i.bye:
                continue
            if i.started:
                recent_games.append(
                    (repr(i) + f" ({i.score_string()})", i.id, i.tournament.nice_name())
                )
            else:
                upcoming_games.append((repr(i), i.id, i.tournament.nice_name()))
        players = [
            (i.name, i.nice_name(), [(k, v) for k, v in i.get_stats().items()])
            for i in team.players
        ]
        return (
            render_template(
                "tournament_specific/each_team_stats.html",
                stats=[(k, v) for k, v in team.get_stats().items()],
                teamName=team.name,
                players=players,
                teamNameClean=team.nice_name(),
                recent_games=recent_games,
                upcoming_games=upcoming_games,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/games/<game_id>/display")
    def scoreboard(tournament, game_id):
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
        players = game.players()
        round_number = game.round_number + 1
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
        return (
            render_template(
                "tournament_specific/scoreboard.html",
                game=game,
                status=status,
                players=players,
                teams=teams,
                official=game.primary_official,
                roundNumber=round_number,
                update_count=game.update_count,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/games/<game_id>/")
    def game_site(tournament, game_id):
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
        for i in get_all_games(comps):
            if not all(
                [
                    k.nice_name() in [j.team.nice_name() for j in i.teams]
                    for k in game.teams
                ]
            ):
                continue
            if i == game:
                continue
            prev_matches.append(
                (
                    f"{repr(i)} ({i.score_string()}) [{i.tournament.name}]",
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
                "tournament_specific/game_page.html",
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

    @app.get("/<tournament>/ladder/")
    def ladder_site(tournament):
        priority = {
            "Team Names": 1,
            "Games Played": 2,
            "Games Won": 1,
            "Percentage": 3,
            "Games Lost": 3,
            "Green Cards": 5,
            "Yellow Cards": 4,
            "Red Cards": 4,
            "Faults": 5,
            "Timeouts Called": 5,
            "Points For": 5,
            "Points Against": 5,
            "Point Difference": 2,
            "ELO": 3,
        }
        teams = [
            (
                i.name,
                i.nice_name(),
                [(v, priority[k]) for k, v in i.get_stats().items()],
            )
            for i in sorted(
                comps[tournament].teams,
                key=lambda a: (
                    -(a.games_won / (a.games_played or 1)),
                    -(a.get_stats()["Point Difference"]),
                ),
            )
        ]
        headers = [
            (i, priority[i])
            for i in (
                ["Team Names"] + [i for i in comps[tournament].teams[0].get_stats()]
            )
        ]
        return (
            render_template(
                "tournament_specific/ladder.html",
                headers=[(i - 1, k, v) for i, (k, v) in enumerate(headers)],
                teams=teams,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/players/")
    def players_site(tournament):
        priority = {
            "Name": 1,
            "B&F Votes": 1,
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
        ]
        headers = ["Name"] + [
            i for i in comps[tournament].teams[0].players[0].get_stats()
        ]
        return (
            render_template(
                "tournament_specific/players.html",
                headers=[(i - 1, k, priority[k]) for i, k in enumerate(headers)],
                players=sorted(players),
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/")
    def player_stats(tournament, player_name):
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
        recent_games = []
        upcoming_games = []
        for i in comps[tournament].games_to_list():
            if player_name not in [j.nice_name() for j in i.players()] or i.bye:
                continue
            if i.started:
                recent_games.append(
                    (repr(i) + f" ({i.score_string()})", i.id, i.tournament.nice_name())
                )
            else:
                upcoming_games.append((repr(i), i.id, i.tournament.nice_name()))
        return (
            render_template(
                "tournament_specific/player_stats.html",
                stats=[(k, v) for k, v in player.get_stats_detailed().items()],
                name=player.name,
                player=player,
                recent_games=recent_games,
                upcoming_games=upcoming_games,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/officials/<nice_name>/")
    def official_site(tournament, nice_name):
        if nice_name not in [i.nice_name() for i in comps[tournament].officials]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Official Does not exist",
                ),
                400,
            )
        official = [
            i for i in comps[tournament].officials if i.nice_name() == nice_name
        ][0]
        recent_games = []
        for i in comps[tournament].games_to_list():
            if official.nice_name() != i.primary_official.nice_name():
                continue
            recent_games.append(
                (
                    f"Round {i.round_number + 1}: {repr(i)} ({i.score_string()})",
                    i.id,
                    i.tournament.nice_name(),
                )
            )
        return (
            render_template(
                "tournament_specific/official.html",
                name=official.name,
                link=official.nice_name(),
                stats=[(k, v) for k, v in official.get_stats().items()],
                games=recent_games,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/officials/")
    def official_directory_site(tournament):
        official = [(i, i.nice_name()) for i in comps[tournament].officials]
        return (
            render_template(
                "tournament_specific/all_officials.html",
                officials=official,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/games/<game_id>/edit/")
    def game_editor(tournament, game_id):
        if int(game_id) >= len(comps[tournament].games_to_list()):
            raise Exception("Game Does not exist!!")
        visual_swap = request.args.get("swap", "false") == "true"
        visual_str = "true" if visual_swap else "false"
        game = comps[tournament].get_game(int(game_id))
        teams = game.teams
        if visual_swap:
            teams = list(reversed(teams))
        key = request.args.get("key", None)
        players = [i for i in game.players()]
        team_one_players = [((1 - i), v) for i, v in enumerate(teams[0].players)]
        team_two_players = [((1 - i), v) for i, v in enumerate(teams[1].players)]
        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif key not in [game.primary_official.key, admin_password]:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        if not game.started:
            return (
                render_template(
                    "tournament_specific/game_editor/game_start.html",
                    players=[i.tidy_name() for i in players],
                    teams=teams,
                    game=game,
                    tournament=f"{tournament}/",
                    swap=visual_str,
                ),
                200,
            )
        elif not game.game_ended():
            for i in teams:
                i.end_timeout()
            return (
                render_template(
                    "tournament_specific/game_editor/edit_game.html",
                    players=[i.tidy_name() for i in players],
                    teamOnePlayers=team_one_players,
                    teamTwoPlayers=team_two_players,
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    tournament=f"{tournament}/",
                ),
                200,
            )
        elif not game.best_player or key == admin_password:
            return (
                render_template(
                    "tournament_specific/game_editor/finalise.html",
                    players=[i.tidy_name() for i in players],
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    tournament=f"{tournament}/",
                ),
                200,
            )
        else:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This game has already been completed!",
                ),
                400,
            )

    @app.get("/<tournament>/games/create")
    def create_game(tournament):
        if not comps[tournament].fixtures_class.manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )
        elif any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        ):
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="There is already a game in progress!",
                ),
                400,
            )
        teams = comps[tournament].teams
        next_id = (
            comps[tournament].fixtures[-1][-1].id if comps[tournament].fixtures else 0
        )
        officials = comps[tournament].officials
        key = request.args.get("key", None)
        if key != admin_password:
            officials = [i for i in officials if i.key == key]
        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif key != admin_password and not officials:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        else:
            return (
                render_template(
                    "tournament_specific/game_editor/create_game_teams.html",
                    tournament=f"{tournament}/",
                    officials=officials,
                    teams=teams,
                    id=next_id,
                ),
                200,
            )

    @app.get("/<tournament>/games/createPlayers")
    def create_game_players(tournament):
        if not comps[tournament].fixtures_class.manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )
        elif any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        ):
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="There is already a game in progress!",
                ),
                400,
            )
        players = sorted(comps[tournament].players(), key=lambda a: a.nice_name())
        next_id = (
            comps[tournament].fixtures[-1][-1].id if comps[tournament].fixtures else 0
        )
        officials = comps[tournament].officials
        key = request.args.get("key", None)
        if key != admin_password:
            officials = [i for i in officials if i.key == key]
        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif key != admin_password and not officials:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        else:
            return (
                render_template(
                    "tournament_specific/game_editor/create_game_players.html",
                    tournament=f"{tournament}/",
                    officials=officials,
                    players=players,
                    id=next_id,
                ),
                200,
            )


def universal_tournament(app, comps: dict[str, Tournament]):
    @app.get("/teams/")
    def universal_stats_directory_site():
        teams = [
            (i.name, i.nice_name())
            for i in sorted(get_all_teams(comps), key=lambda a: a.nice_name())
        ]
        return (
            render_template(
                "tournament_specific/stats.html", teams=teams, tournament=""
            ),
            200,
        )

    @app.get("/teams/<team_name>/")
    def universal_stats_site(team_name):
        team = [i for i in get_all_teams(comps) if team_name == i.nice_name()][0]
        recent_games = []
        upcoming_games = []
        for c in comps.values():
            for i in c.games_to_list():
                if team_name not in [j.team.nice_name() for j in i.teams] or i.bye:
                    continue
                if i.started:
                    recent_games.append(
                        (
                            repr(i) + f" ({i.score_string()}) [{c.name}]",
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )
                else:
                    upcoming_games.append(
                        (
                            repr(i) + f" [{c.name}]",
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
                "tournament_specific/each_team_stats.html",
                stats=[(k, v) for k, v in team.get_stats().items()],
                teamName=team.name,
                players=players,
                teamNameClean=team.nice_name(),
                recent_games=recent_games,
                upcoming_games=upcoming_games,
                tournament="",
            ),
            200,
        )

    @app.get("/ladder/")
    def universal_ladder_site():
        priority = {
            "Team Names": 1,
            "Games Played": 2,
            "Games Won": 1,
            "Percentage": 2,
            "Games Lost": 3,
            "Green Cards": 5,
            "Yellow Cards": 4,
            "Red Cards": 4,
            "Faults": 5,
            "Timeouts Called": 5,
            "Points For": 5,
            "Points Against": 5,
            "Point Difference": 2,
            "ELO": 3,
        }
        teams = [
            (
                i.name,
                i.nice_name(),
                [(v, priority[k]) for k, v in i.get_stats().items()],
            )
            for i in sorted(
                get_all_teams(comps),
                key=lambda a: (-a.games_won, -(a.get_stats()["Point Difference"])),
            )
        ]
        headers = [
            (i, priority[i])
            for i in (["Team Names"] + [i for i in get_all_teams(comps)[0].get_stats()])
        ]
        return (
            render_template(
                "tournament_specific/ladder.html",
                headers=[(i - 1, k, v) for i, (k, v) in enumerate(headers)],
                teams=teams,
                tournament="",
            ),
            200,
        )

    @app.get("/players/")
    def universal_players_site():
        priority = {
            "Name": 1,
            "B&F Votes": 1,
            "Points scored": 2,
            "Aces scored": 2,
            "Faults": 5,
            "Double Faults": 5,
            "Green Cards": 4,
            "Yellow Cards": 3,
            "Red Cards": 3,
            "Rounds on Court": 5,
            "Rounds Carded": 5,
            "Games Played": 3,
            "Games Won": 2,
        }
        all_players = get_all_players(comps)
        players = [
            (
                i.name,
                i.team.nice_name(),
                i.nice_name(),
                [(v, priority[k]) for k, v in i.get_stats().items()],
            )
            for i in all_players
        ]
        headers = ["Name"] + [i for i in get_all_teams(comps)[0].players[0].get_stats()]
        return (
            render_template(
                "tournament_specific/players.html",
                headers=[(i - 1, k, priority[k]) for i, k in enumerate(headers)],
                players=players,
                tournament="",
            ),
            200,
        )

    @app.get("/players/<player_name>/")
    def universal_player_stats(player_name):
        if player_name not in [i.nice_name() for i in get_all_players(comps)]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        player = [i for i in get_all_players(comps) if player_name == i.nice_name()][0]
        recent_games = []
        upcoming_games = []
        for i in get_all_games(comps):
            if player_name not in [j.nice_name() for j in i.players()] or i.bye:
                continue
            if i.started:
                recent_games.append(
                    (repr(i) + f" ({i.score_string()})", i.id, i.tournament.nice_name())
                )
            else:
                upcoming_games.append((repr(i), i.id, i.tournament.nice_name()))
        return (
            render_template(
                "tournament_specific/player_stats.html",
                stats=[(k, v) for k, v in player.get_stats_detailed().items()],
                name=player.name,
                player=player,
                recent_games=recent_games,
                upcoming_games=upcoming_games,
                tournament=f"",
            ),
            200,
        )

    @app.get("/officials/<nice_name>/")
    def universal_official_site(nice_name):
        official = [i for i in get_all_officials(comps) if i.nice_name() == nice_name][
            0
        ]
        recent_games = []
        for i in get_all_games(comps):
            if official.nice_name() != i.primary_official.nice_name():
                continue
            recent_games.append(
                (
                    f"Round {i.round_number + 1}: {repr(i)} ({i.score_string()})",
                    i.id,
                    i.tournament.nice_name(),
                )
            )
        return (
            render_template(
                "tournament_specific/official.html",
                name=official.name,
                link=official.nice_name(),
                stats=[(k, v) for k, v in official.get_stats().items()],
                games=recent_games,
                tournament="",
            ),
            200,
        )

    @app.get("/officials/")
    def universal_official_directory_site():
        official = [(i, i.nice_name()) for i in get_all_officials(comps)]
        return (
            render_template(
                "tournament_specific/all_officials.html",
                officials=official,
                tournament="",
            ),
            200,
        )
