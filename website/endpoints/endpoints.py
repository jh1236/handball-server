import io
import os
from typing import Callable

import numpy as np
from flask import request, send_file, Response, render_template
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from structure.AllTournament import get_all_players, get_all_games
from structure.GameUtils import filter_games, get_query_descriptor
from utils.logging_handler import logger
from website.endpoints.clips import add_clip_endpoints
from website.endpoints.edit_game import add_game_endpoints
from website.endpoints.graph import add_graph_endpoints
from website.endpoints.tournament import add_tourney_endpoints


def add_endpoints(app, comps):
    @app.get("/api/teams")
    def teams():
        tournament = request.args.get("tournament", type=str)
        return {i.name: [j.name for j in i.players] for i in comps[tournament].teams}

    @app.get("/api/tournaments")
    def tournaments():
        return list(comps.values())

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
        if os.path.isfile(f"./resources/images/teams/{team}.png"):
            return send_file(
                f"./resources/images/users/{team}.png", mimetype="image/png"
            )
        else:
            return send_file(f"./resources/images/umpire.png", mimetype="image/png")

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



    add_tourney_endpoints(app, comps)
    add_graph_endpoints(app)
    add_game_endpoints(app, comps)
    # add_clip_endpoints(app, comps)
