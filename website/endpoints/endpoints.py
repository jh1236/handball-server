import io
import os
from typing import Callable

import numpy as np
from flask import request, send_file, Response
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

    @app.get("/api/game/find")
    def game_finder():
        details: set[str]
        games: list[tuple[object, set]]
        games, details = filter_games(get_all_games(), request.args, get_details=True)
        print("\n".join(f"'{k}': '{v}'" for k, v in request.args.items(multi=True)))
        if not games and any("," in i for i in request.args.values()):
            return (
                "<h1>Nothing Found.  Have you put a comma instead of an ampersand?</h1>"
            )
        output = [
            f"<h1>Query returned {len(games)} results</h1>",
            "<p>" + get_query_descriptor(details) + "</p>",
        ]
        for g, players in games:
            s = f'<p><a href = "/{g.tournament.nice_name()}/games/{g.id}">'
            s += g.full_name
            if details:
                s += " - "
            for p in g.all_players:
                if p.nice_name() not in players or not details:
                    continue
                s += f"({p.first_name()}: "
                for j in details:
                    stat = (p.get_game_details() | p.get_stats_detailed())[j]
                    if isinstance(stat, str):
                        s += f"{j}={stat},"
                    else:
                        s += f"{j}={round(stat, 2)},"
                s += ")"

            s += "</a></p>"
            output.append(s)
        return "\n".join(output)

    add_tourney_endpoints(app, comps)
    add_graph_endpoints(app, comps)
    add_game_endpoints(app, comps)
    add_clip_endpoints(app, comps)
