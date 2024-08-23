import random

from flask import send_file, request

import utils.permissions
from database.models import PlayerGameStats, People, Tournaments
from structure.GameUtils import filter_games, get_query_descriptor
from utils.permissions import fetch_user, officials_only
from utils.sidebar_wrapper import render_template_sidebar
from website.endpoints.endpoints import add_endpoints

numbers = ["Zero", "One", "Two", "Three", "Four", "Five", "Six"]


def init_api(app):

    add_endpoints(app)

    @app.get("/")
    def root():
        comps = Tournaments.query.all()
        return (
            render_template_sidebar(
                "all_tournaments.html",
                comps=comps,
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
            @app.get("/test/login")
    @officials_only
    def user_page2():
        key = fetch_user()
        user = People.query.filter(People.password == key).first()

        return """
        <html><body>
            <form action="/test/login" method="post">
            <input type="text" id="name" name="name">
            <input type="email" id="email" name="email">
            <input type="submit" value="Submit">
            </form>
        </body></html>
    """, 200
    
    @app.post("/api/login/check")
    def login2():
        print(str(request.method) + " hi2")
        print(str(request.form) + " hello2")
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        if utils.permissions.check_password(user_id, password):
            token =  utils.permissions.get_token(user_id, password)
            # set cookie to token
            response = "Logged in", 200
            response.set_cookie('token', token)
            response.set_cookie('userID', user_id)
            response.set_cookie('userName', People.query.filter(People.id == user_id).first().name)
            return response
        print("access denied")
        return "Access Denied", 403
    
    @app.get("/api/login")
    def login():
        return render_template_sidebar("permissions/login.html", error=""), 200
        print(str(request.method) + " hi")
        print(str(request.form) + " hello")
        if request.method == "POST":
            user_id = request.form.get("user_id")
            password = request.form.get("password")
            if utils.permissions.check_password(user_id, password):
                token =  utils.permissions.get_token(user_id, password)
                # set cookie to token
                response = "Logged in", 200
                response.set_cookie('token', token)
                response.set_cookie('userID', user_id)
                response.set_cookie('userName', People.query.filter(People.id == user_id).first().name)
                return response
            return render_template_sidebar("permissions/login.html", error="Incorrect Password or Username"), 200

    @app.get("/favicon.ico/")
    def icon():
        return send_file("./static/favicon.ico")

    @app.get("/user/")
    @officials_only
    def user_page():
        key = fetch_user()
        user = People.query.filter(People.password == key).first()

        return "Todo", 500

    @app.get("/find")
    def game_finder():
        details: set[str]
        games: list[tuple[object, set]]
        games, details = filter_games(request.args, get_details=True)
        print("\n".join(f"'{k}': '{v}'" for k, v in request.args.items(multi=True)))
        if not games and any("," in i for i in request.args.values()):
            return (
                "<h1>Nothing Found.  Have you put a comma instead of an ampersand?</h1>"
            )
        return render_template_sidebar(
            "game_finder.html",
            query=get_query_descriptor(details),
            games=games,
            args=request.args,
            details=[i for i in details if i and i not in ["Count", "Player"]],
            headings=sorted(
                (
                    PlayerGameStats.rows
                )
            ),
        )

    from website.tournament_specific import add_tournament_specific
    from website.admin import add_admin_pages
    from website.universal_stats import add_universal_tournament

    add_tournament_specific(app)
    add_universal_tournament(app)
    add_admin_pages(app)


def sign(elo_delta):
    if elo_delta >= 0:
        return "+"
    else:
        return "-"
