import random

from flask import render_template, send_file

from structure.AllTournament import get_all_officials, get_all_players
from structure.Tournament import Tournament
from utils.permissions import fetch_user, officials_only
from website.endpoints.endpoints import add_endpoints

numbers = ["One", "Two", "Three", "Four", "Five", "Six"]


def init_api(app, comps: dict[str, Tournament]):

    add_endpoints(app, comps)

    @app.get("/")
    def root():
        return (
            render_template(
                "all_tournaments.html",
                comps=comps.values(),
            ),
            200,
        )

    @app.get("/documents/")
    def docs():
        return (
            render_template("rules.html"),
            200,
        )

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
        player = next(i for i in get_all_players() if i.nice_name() == user.nice_name())
        with open("./clips/required.txt") as fp:
            reqd = [i.strip() for i in fp.readlines()]
        from website.clips import answers

        seen_videos = [str(j["id"]) for j in answers if j["name"] == user.nice_name()]
        reqd = [i for i in reqd if i not in seen_videos]
        if len(reqd) > 4:
            reqd = reqd[:4]
        return render_template("user_file.html", user=user, player=player, reqd=reqd)

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