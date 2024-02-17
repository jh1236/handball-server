from flask import render_template, request, redirect, Response

from structure.AllTournament import (
    get_all_games,
    get_all_officials,
)
from structure.GameUtils import game_string_to_commentary
from structure.Tournament import Tournament
from utils.util import fixture_sorter
from website.website import numbers, sign


def add_tournament_specific(app, comps: dict[str, Tournament]):
    @app.get("/<tournament>/")
    def home_page(tournament):
        in_progress = any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        )
        ladder = comps[tournament].ladder()
        if isinstance(ladder[0], list):
            ladder = [
                (
                    f"Pool {numbers[i]}",
                    list(enumerate(l if len(l) < 10 else l[:10], start=1)),
                )
                for i, l in enumerate(ladder)
            ]
        else:
            ladder = [
                (
                    "",
                    list(
                        enumerate(ladder if len(ladder) < 10 else ladder[:10], start=1)
                    ),
                )
            ]
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
        players.sort(key=lambda a: -a.votes)
        if len(players) > 10:
            players = players[0:10]

        notes = comps[tournament].notes or "Notices will appear here when posted"
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
                ladder=ladder,
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
                [
                    j
                    for j in i
                    if player
                    in [
                        k.nice_name()
                        for k in [*j.players(), j.scorer, j.primary_official]
                    ]
                ]
                for i in fixtures
            ]
            finals = [
                [
                    j
                    for j in i
                    if player
                    in [
                        k.nice_name()
                        for k in [*j.players(), j.scorer, j.primary_official]
                    ]
                ]
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
                "tournament_specific/site_detailed.html",
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

    @app.get("/<tournament>/teams/")
    def stats_directory_site(tournament):
        teams = [
            i
            for i in sorted(comps[tournament].teams, key=lambda a: a.nice_name())
            if i.games_played > 0 or len(comps[tournament].teams) < 15
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
            if team not in [j.team for j in i.teams] or i.bye or not i.ranked:
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
            else:
                upcoming_games.append((repr(i), i.id, i.tournament.nice_name()))
        while len(recent_games) + len(upcoming_games) > 20:
            if len(recent_games) > 10:
                recent_games.pop(0)
            else:
                upcoming_games.pop(0)
        players = [
            (i.name, i.nice_name(), [(k, v) for k, v in i.get_stats().items()])
            for i in team.players
        ]
        return (
            render_template(
                "tournament_specific/each_team_stats.html",
                stats=[(k, v) for k, v in team.get_stats().items()],
                team=team,
                recent_games=recent_games,
                upcoming_games=upcoming_games,
                tournament=f"{tournament}/",
                players=players,
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
        visual_swap = request.args.get("swap", "false") == "true"
        teams = game.teams
        if visual_swap:
            teams = list(reversed(teams))
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
                timeout_time=max([i.time_out_time + 30 for i in game.teams]) * 1000,
                serve_time=(game.serve_clock + 8) * 1000,
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
        team_dicts = []
        for i in teams:
            elo_display = {
                "ELO": f"{i.elo_at_start}"
                + (
                    f"  [{sign(i.elo_delta)}{round(abs(i.elo_delta), 2)}]"
                    if game.best_player and i.elo_delta is not None
                    else ""
                )
            }
            team_dicts.append(elo_display | i.get_stats())
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
            status = "In timeout"
        elif not game.game_ended():
            status = "Game in progress"
        elif not game.best_player:
            status = "Finished"
        else:
            status = "Official"
        player_stats = [
            (
                "ELO Delta",
                *[
                    (
                        f"{round(j.elo_at_start, 2)}"
                        + (
                            f"  [{sign(j.elo_delta)}{round(abs(j.elo_delta), 2)}]"
                            if j.elo_delta
                            else "  [+0]"
                        )
                    )
                    for j in players
                ],
            )
        ] + [(i, *[j.get_stats()[i] for j in players]) for i in players[0].get_stats()]
        print(player_stats)
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
            "Elo": 3,
        }
        ladder = comps[tournament].ladder()
        if isinstance(ladder[0], list):
            ladder = [
                (f"Pool {numbers[i]}", list(enumerate(l, start=1)))
                for i, l in enumerate(ladder)
            ]
        else:
            ladder = [("", list(enumerate(ladder, start=1)))]
        ladder = [(i if len(i) <= 10 else i[:10]) for i in ladder]
        teams = [
            (
                [
                    (
                        j.short_name,
                        j.nice_name(),
                        j.image(),
                        [(v, priority[k]) for k, v in j.get_stats().items()],
                    )
                    for _, j in l[1]
                    if j.games_played > 0 or len(comps[tournament].teams) < 15
                ],
                l[0],
                k,
            )
            for k, l in enumerate(ladder)
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
                "tournament_specific/players.html",
                headers=[(i - 1, k, priority[k]) for i, k in enumerate(headers)],
                players=sorted(players),
                tournament=f"{tournament}/"
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
            if player_name not in [j.nice_name() for j in i.players()] or i.bye or not i.ranked:
                continue
            gt = next(
                t for t in i.teams if player_name in [j.nice_name() for j in t.players]
            )
            gp = next(p for p in gt.players if player_name == p.nice_name())
            s = " <+0>"
            if gt.elo_delta:
                s = f" <{sign(gp.elo_delta)}{round(abs(gp.elo_delta), 2)}>"
            if i.started:
                recent_games.append(
                    (
                        i.full_name + s,
                        i.id,
                        i.tournament.nice_name(),
                    )
                )
            else:
                upcoming_games.append((repr(i), i.id, i.tournament.nice_name()))
        while len(recent_games) + len(upcoming_games) > 20:
            if len(recent_games) > 10:
                recent_games.pop(0)
            else:
                upcoming_games.pop(0)
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
            if official.nice_name() == i.primary_official.nice_name():
                recent_games.append(
                    (
                        f"{'Umpire ' if comps[tournament].details.get('scorer', False) else ''}Round {i.round_number + 1}: {repr(i)} ({i.score_string()})",
                        i.id,
                        i.tournament.nice_name(),
                    )
                )
            elif official.nice_name() == i.scorer.nice_name():
                recent_games.append(
                    (
                        f"Scorer Round {i.round_number + 1}: {repr(i)} ({i.score_string()})",
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
        team_one_players = [((1 - i), v) for i, v in enumerate(teams[0].players[:2])]
        team_two_players = [((1 - i), v) for i, v in enumerate(teams[1].players[:2])]
        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif key not in [game.primary_official.key, game.scorer.key] + [i.key for i in get_all_officials() if i.admin]:
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
            # for i in teams:
            #     i.end_timeout()
            timeout_team = max(game.teams, key=lambda a: a.time_out_time)
            return (
                render_template(
                    "tournament_specific/game_editor/edit_game.html",
                    players=[i.tidy_name() for i in players],
                    teamOnePlayers=team_one_players,
                    teamTwoPlayers=team_two_players,
                    swap=visual_str,
                    teams=teams,
                    enum_teams=enumerate(teams),
                    game=game,
                    timeout_time=30000
                    + max(i.time_out_time for i in game.teams) * 1000,
                    timeout_first=1 - game.teams.index(timeout_team),
                    tournament=f"{tournament}/",
                ),
                200,
            )
        elif game.protested is None:
            team_dicts = [i.get_stats() for i in teams]
            return (
                render_template(
                    "tournament_specific/game_editor/team_signatures.html",
                    players=[i.tidy_name() for i in players],
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    player_stats=[
                        (i, *[j.get_stats()[i] for j in players])
                        for i in players[0].get_stats()
                    ],
                    stats=[(i, *[j[i] for j in team_dicts]) for i in team_dicts[0]],
                    tournament=f"{tournament}/",
                ),
                200,
            )
        elif not game.best_player or key in [i.key for i in get_all_officials() if i.admin]:
            return (
                render_template(
                    "tournament_specific/game_editor/finalise.html",
                    players=[i.tidy_name() for i in players],
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    cards=enumerate(game.cards, start=1),
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

    @app.get("/<tournament>/create")
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
        officials = comps[tournament].officials.copy()
        key = request.args.get("key", None)
        if key not in [i.key for i in get_all_officials() if i.admin]:
            officials = [i for i in officials if i.key == key]
        else:
            official = [i for i in officials if i.key == key]
            officials = official + [i for i in officials if i.key != key]

        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif not officials:
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

    @app.get("/<tournament>/round")
    def new_round_site(tournament):
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
        key = request.args.get("key", None)
        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif key not in [i.key for i in get_all_officials() if i.admin]:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        else:
            comps[tournament].update_games(True)
            comps[tournament].update_games()
            comps[tournament].save()
            return redirect(f"/{comps[tournament].nice_name()}/", code=302)

    @app.get("/<tournament>/createPlayers")
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
        if key not in [i.key for i in get_all_officials() if i.admin]:
            officials = [i for i in officials if i.key == key]
        else:
            official = [i for i in officials if i.key == key]
            officials = official + [i for i in officials if i.key != key]
        if key is None:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="This page requires a password to access:",
                ),
                403,
            )
        elif not officials:
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

    @app.get("/<tournament>/raw/")
    def raw_tournament(tournament):
        t = comps[tournament]
        players = t.players()
        headers = players[0].get_stats_detailed().keys()
        string = "Name," + ",".join(headers)
        for i in players:
            string += "\n"
            string += ",".join(
                [i.name] + [str(j) for j in i.get_stats_detailed().values()]
            )
        response = Response(string, content_type="text/csv")
        response.headers[
            "Content-Disposition"
        ] = f"attachment; filename={tournament}.csv"
        return response
