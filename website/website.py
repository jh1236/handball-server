import random

from flask import send_file, request

import utils.permissions
from database import db
from database.models import PlayerGameStats, Tournaments, Officials, Games
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

    @app.get("/robots.txt")
    def robots():
        return send_file("./resources/robots.txt")
    
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
        user = fetch_user()
        umpire = Officials.query.filter(Officials.person_id == user.id).first()
        recent = db.session.query(Games).join(PlayerGameStats,
                                              PlayerGameStats.game_id == Games.id).filter(
            Games.is_bye == False, (Games.official_id == umpire.id) | (Games.scorer_id == umpire.id) | (
                        PlayerGameStats.player_id == user.id), ).order_by(Games.started, -Games.start_time, Games.id).group_by(
            Games.id).limit(10).all()
        return render_template_sidebar("user_file.html", user=fetch_user(), umpire=umpire, recent=recent), 200

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
