import os

from flask import request, send_file

from utils.databaseManager import DatabaseManager, dict_factory
from utils.logging_handler import logger
from website.endpoints.game.edit_game import add_edit_game_endpoints
from website.endpoints.game.get_game import add_get_game_endpoints
from website.endpoints.graph import add_graph_endpoints
from website.endpoints.officials.officials import add_get_official_endpoints
from website.endpoints.players.players import add_get_player_endpoints
from website.endpoints.players.user import add_user_endpoints
from website.endpoints.teams.get_teams import add_get_teams_endpoints
from website.endpoints.tournaments.tournament import add_tourney_endpoints


def add_endpoints(app):

    @app.get("/api/image")
    def image():
        team = request.args.get("name", type=str)
        return send_file(f"./resources/images/{team}.png", mimetype="image/png")

    # TODO: THIS IS VERY UNSECURE!!
    @app.get("/api/request")
    def request_call():
        query = request.args.get("query", type=str)
        logger.info(f"Query for DB: {query}")
        if ("token" in query.lower() or "password" in query.lower()) and "people" in query.lower():
            return "No token for you", 403
        with DatabaseManager(read_only=True) as conn:
            conn.row_factory = dict_factory
            out = [i for i in conn.execute(query).fetchall()]
        for i in out:
            if "session_token" in i:
                del i["session_token"]
            if "token_timeout" in i:
                del i["token_timeout"]
            if "password" in i:
                del i["password"]
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
    add_edit_game_endpoints(app)
    add_get_game_endpoints(app)
    add_user_endpoints(app)
    add_get_teams_endpoints(app)
    add_get_player_endpoints(app)
    add_get_official_endpoints(app)
