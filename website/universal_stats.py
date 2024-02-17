from flask import render_template, Response

from structure.AllTournament import (
    get_all_teams,
    get_all_players,
    get_all_officials,
    get_all_games,
)
from structure.Tournament import Tournament
from website.website import sign


def add_universal_tournament(app, comps: dict[str, Tournament]):
    @app.get("/teams/")
    def universal_stats_directory_site():
        teams = [
            i
            for i in sorted(get_all_teams(), key=lambda a: a.nice_name())
            if i.games_played > 0
        ]
        return (
            render_template(
                "tournament_specific/stats.html", teams=teams, tournament=""
            ),
            200,
        )

    @app.get("/teams/<team_name>/")
    def universal_stats_site(team_name):
        team = [i for i in get_all_teams() if team_name == i.nice_name()][0]
        recent_games = []
        upcoming_games = []
        for c in comps.values():
            for i in c.games_to_list():
                if team_name not in [j.team.nice_name() for j in i.teams] or i.bye or not i.ranked:
                    continue
                if i.started:
                    gt = next(j for j in i.teams if j.nice_name() == team_name)
                    s = " <+0>"
                    if gt.elo_delta:
                        s = f" <{sign(gt.elo_delta)}{round(abs(gt.elo_delta), 2)}>"
                    recent_games.append(
                        (
                            i.full_name + s,
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )
                else:
                    upcoming_games.append(
                        (
                            i.full_name,
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )
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
                players=players,
                team=team,
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
            "Elo": 3,
        }
        ladder = [
            (
                "",
                list(
                    enumerate(
                        sorted(
                            get_all_teams(),
                            key=lambda a: (
                                -a.games_won,
                                -(a.get_stats()["Point Difference"]),
                            ),
                        ),
                        start=1,
                    )
                ),
            )
        ]
        ladder = [(i if len(i) <= 10 else i[:10]) for i in ladder]
        print(ladder)
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
                    if j.games_played > 0
                ],
                l[0],
                k,
            )
            for k, l in enumerate(ladder)
        ]
        teams_two = []
        headers = [
            (i, priority[i])
            for i in (["Team Names"] + [i for i in get_all_teams()[0].get_stats()])
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
            "Elo": 2,
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
        all_players = get_all_players()
        players = [
            (
                i.name,
                i.team.nice_name(),
                i.nice_name(),
                [(v, priority[k]) for k, v in i.get_stats().items()],
            )
            for i in all_players
            if not i.nice_name().startswith("null")
        ]
        headers = ["Name"] + [i for i in get_all_teams()[0].players[0].get_stats()]
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
        if player_name not in [i.nice_name() for i in get_all_players()]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        player = [i for i in get_all_players() if player_name == i.nice_name()][0]
        recent_games = []
        upcoming_games = []
        for c in comps.values():
            for i in c.games_to_list():
                if player_name not in [j.nice_name() for j in i.players()] or i.bye or not i.ranked:
                    continue
                gt = next(
                    t
                    for t in i.teams
                    if player_name in [j.nice_name() for j in t.players]
                )
                gp = next(p for p in gt.players if player_name == p.nice_name())
                s = " <+0>"
                if gp.elo_delta:
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
                    upcoming_games.append(
                        (
                            i.full_name,
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )
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
                tournament=f"",
            ),
            200,
        )

    @app.get("/officials/<nice_name>/")
    def universal_official_site(nice_name):
        official = [i for i in get_all_officials() if i.nice_name() == nice_name][0]
        recent_games = []
        for i in get_all_games():
            if official.nice_name() == i.primary_official.nice_name():
                recent_games.append(
                    (
                        f"Umpire Round {i.round_number + 1}: {repr(i)} ({i.score_string()}) [{i.tournament.name}]",
                        i.id,
                        i.tournament.nice_name(),
                    )
                )
            elif official.nice_name() == i.scorer.nice_name():
                recent_games.append(
                    (
                        f"Scorer Round {i.round_number + 1}: {repr(i)} ({i.score_string()}) [{i.tournament.name}]",
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
        official = [(i, i.nice_name()) for i in get_all_officials()]
        return (
            render_template(
                "tournament_specific/all_officials.html",
                officials=official,
                tournament="",
            ),
            200,
        )

    @app.get("/signup/")
    def sign_up_page():
        tournament = "Fifth S.U.S.S Championship"
        return (
            render_template(
                "sign_up/new.html",
                tournament=tournament,
            ),
            200,
        )

    @app.get("/raw/")
    def raw():
        players = get_all_players()
        headers = players[0].get_stats_detailed().keys()
        string = "Name," + ",".join(headers)
        for i in players:
            string += "\n"
            string += ",".join(
                [i.name] + [str(j) for j in i.get_stats_detailed().values()]
            )
        response = Response(string, content_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=all_games.csv"
        return response
