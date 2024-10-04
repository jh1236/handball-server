import os

from flask import request, send_file
from sqlalchemy import text

from database import db
from utils.databaseManager import DatabaseManager
from utils.logging_handler import logger
from website.endpoints.edit_game import add_game_endpoints
from website.endpoints.graph import add_graph_endpoints
from website.endpoints.tournament import add_tourney_endpoints
from website.endpoints.user import add_user_endpoints


def add_endpoints(app):
    @app.get("/api/teams/image")
    def team_image():
        team = request.args.get("name", type=str)
        if os.path.isfile(f"./resources/images/teams/{team}.png"):
            return send_file(
                f"./resources/images/teams/{team}.png", mimetype="image/png"
            )
        else:
            return send_file(
                f"./resources/images/teams/blank.png", mimetype="image/png"
            )

    @app.get("/api/image")
    def image():
        team = request.args.get("name", type=str)
        return send_file(f"./resources/images/{team}.png", mimetype="image/png")

    @app.get("/api/users/image")
    def user_image():
        team = request.args.get("name", type=str)
        if os.path.isfile(f"./resources/images/users/{team}.png"):
            return send_file(
                f"./resources/images/users/{team}.png", mimetype="image/png"
            )
        else:
            return send_file(f"./resources/images/umpire.png", mimetype="image/png")

    @app.get("/api/request")
    def request_call():
        query = request.args.get("query", type=str)
        with db.session.connection().execution_options(postgresql_readonly=True) as conn:
            out = [dict(i._mapping) for i in conn.execute(text(query)).all()]
        return out

    # testing related endpoints
    @app.get("/api/mirror")
    def mirror():
        logger.info(f"Request for score: {request.args}")
        d = dict(request.args)
        if not d:
            d = {
                "All these webs on me": " You think I'm Spiderman",
                "Shout out": "martin luther King",
                "this is the sound of a robot": "ELELALAELE-BING-ALELILLELALE",
            }
        return str(d), 200

    add_tourney_endpoints(app)
    add_graph_endpoints(app)
    add_game_endpoints(app)
    add_user_endpoints(app)
