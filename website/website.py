import random

from flask import render_template, send_file, request

from structure.Tournament import Tournament
from website.endpoints.endpoints import add_endpoints

numbers = ["One", "Two", "Three", "Four", "Five", "Six"]


def init_api(app, comps: dict[str, Tournament]):
    from start import admin_password
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
        return send_file("../resources/documents/pdf/rules.pdf"), 200

    @app.get("/rules/simple")
    def simple_rules():
        return send_file("../resources/documents/pdf/rules_simple.pdf"), 200

    @app.get("/rules/proposed")
    def new_rules():
        return send_file("../resources/documents/pdf/proposed_rules.pdf"), 200

    @app.get("/code_of_conduct/")
    def code_of_conduct():
        rand = random.Random()
        if rand.randrange(0, 10):
            return send_file("../resources/documents/pdf/code_of_conduct_2.pdf"), 200
        return send_file("../resources/documents/pdf/code_of_conduct.pdf"), 200

    @app.get("/favicon.ico/")
    def icon():
        return send_file("../static/favicon.ico")

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

