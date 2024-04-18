import random

from flask import render_template, send_file, request

import utils.permissions
from structure.AllTournament import get_all_officials, get_all_players, get_all_games
from structure.GameUtils import filter_games, get_query_descriptor
from structure.Tournament import Tournament
from utils.permissions import fetch_user, officials_only
from utils.sidebar_wrapper import render_template_sidebar
from website.endpoints.endpoints import add_endpoints

numbers = ["One", "Two", "Three", "Four", "Five", "Six"]


def init_api(app, comps: dict[str, Tournament]):

    add_endpoints(app, comps)

    @app.get("/")
    def root():
        return (
            render_template_sidebar(
                "all_tournaments.html",
                comps=comps.values(),
            ),
            200,
        )

    @app.get("/pipe.mp3")
    def pipe():
        return send_file("./resources/pipe.mp3")

    @app.get("/documents/")
    def docs():
        return render_template_sidebar("rules.html"), 200


    @app.get("/logout/")
    def logout():
        return utils.permissions.logout()

    @app.get("/rules/current")
    def rules():
        return send_file("./resources/documents/pdf/rules.pdf"), 200

    @app.get("/rules/simple")
    def simple_rules():
        return send_file("./resources/documents/pdf/rules_simple.pdf"), 200

    @app.get("/rules/proposed")
    def new_rules():
        return send_file("./resources/documents/pdf/proposed_rules.pdf"), 200

    @app.get("/code_of_conduct/")
    def code_of_conduct():
        rand = random.Random()
        if rand.randrange(1, 10):
            return send_file("./resources/documents/pdf/code_of_conduct_2.pdf"), 200
        return send_file("./resources/documents/pdf/code_of_conduct.pdf"), 200

    @app.get("/favicon.ico/")
    def icon():
        return send_file("./static/favicon.ico")

    @app.get("/user/")
    @officials_only
    def user_page():
        key = fetch_user()
        user = next(i for i in get_all_officials() if i.key == key)
        player = (
            [i for i in get_all_players() if i.nice_name() == user.nice_name()]
            + ["This will never match!"]
        )[0]
        with open("./clips/required.txt") as fp:
            reqd = [i.strip() for i in fp.readlines()]
        from website.clips import answers

        seen_videos = [str(j["id"]) for j in answers if j["name"] == user.nice_name()]
        reqd = [i for i in reqd if i not in seen_videos]
        all_games = get_all_games()
        to_officiate = []
        to_play = []
        for i in all_games:
            if i.best_player:
                continue
            if user.nice_name() in [
                i.primary_official.nice_name(),
                i.scorer.nice_name(),
            ]:
                to_officiate.append(i)
            if user.nice_name() in [k.nice_name() for k in i.all_players]:
                to_play.append(i)
        if len(reqd) > 4:
            reqd = reqd[:4]
        if len(to_officiate) > 4:
            to_officiate = to_officiate[:4]
        if len(to_play) > 4:
            to_play = to_play[:4]
        return render_template_sidebar(
            "user_file.html",
            user=user,
            player=player,
            reqd=reqd,
            to_play=to_play,
            to_officiate=to_officiate,
        )

    @app.get("/find")
    def game_finder():
        details: set[str]
        games: list[tuple[object, set]]
        games, details = filter_games(get_all_games(), request.args, get_details=True)
        print("\n".join(f"'{k}': '{v}'" for k, v in request.args.items(multi=True)))
        if not games and any("," in i for i in request.args.values()):
            return (
                "<h1>Nothing Found.  Have you put a comma instead of an ampersand?</h1>"
            )
        return render_template(
            "game_finder.html",
            query=get_query_descriptor(details),
            games=games,
            args=request.args,
            details=[i for i in details if i and i not in ["Count", "Player"]],
            headings=sorted(
                (
                    (p := get_all_games()[0].all_players[0]).get_stats_detailed()
                    | p.get_game_details()
                    | {"Count": 1}
                )
            ),
        )

    from website.tournament_specific import add_tournament_specific
    from website.admin import add_admin_pages
    from website.universal_stats import add_universal_tournament
    from website.clips import add_video_player

    add_video_player(app, comps)
    add_tournament_specific(app, comps)
    add_universal_tournament(app, comps)
    add_admin_pages(app, comps)


def sign(elo_delta):
    if elo_delta >= 0:
        return "+"
    else:
        return "-"
