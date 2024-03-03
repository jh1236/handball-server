import io
import os

import numpy as np
from flask import request, send_file, Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from structure.AllTournament import get_all_players, get_all_games
from utils.logging_handler import logger
from website.endpoints.clips import add_clip_endpoints
from website.endpoints.edit_game import add_game_endpoints
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
        return send_file(f"./resources/images/users/{team}.png", mimetype="image/png")

    @app.get("/graph")
    def plot_png():
        x = request.args.get("x", type=str)
        y = request.args.get("y", type=str)
        tournament = request.args.get("tournament", type=str,default=None)
        fig = create_figure(x, y, tournament)
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        return Response(output.getvalue(), mimetype="image/png")

    @app.get("/graph_player")
    def player_plot_png():
        x = request.args.get("x", type=str)
        y = request.args.get("y", type=str)
        player = request.args.get("player", type=str)
        tournament = request.args.get("tournament", type=str,default=None)
        fig = create_figure_player(x, y, player, tournament)
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        return Response(output.getvalue(), mimetype="image/png")

    def create_figure_player(x_stat, y_stat, player, tournament):
        fig = Figure()
        axis = fig.add_subplot(1, 1, 1)
        if tournament:
            players = [next(k for k in i.all_players() if k.nice_name() == player) for i in comps[tournament].games_to_list() if player in [j.nice_name() for j in i.all_players()]]
        else:
            players = [next(k for k in i.all_players() if k.nice_name() == player) for i in get_all_games() if player in [j.nice_name() for j in i.all_players()]]
        xs = np.array([float(str(i.get_stats_detailed()[x_stat]).strip("%").replace("∞", "inf")) for i in players])
        ys = np.array([float(str(i.get_stats_detailed()[y_stat]).strip("%").replace("∞", "inf")) for i in players])
        axis.scatter(xs, ys)
        a, b = np.polyfit(xs, ys, 1)
        axis.plot(xs, a*xs+b)
        fig.supxlabel(x_stat)
        fig.supylabel(y_stat)
        return fig

    def create_figure(x_stat, y_stat, tournament):
        fig = Figure()
        axis = fig.add_subplot(1, 1, 1)
        if tournament:
            players = [i for i in comps[tournament].players()]
        else:
            players = [i for i in get_all_players()]
        xs = np.array([float(str(i.get_stats_detailed()[x_stat]).strip("%").replace("∞", "inf")) for i in players if i.get_stats()["Rounds on Court"]])
        ys = np.array([float(str(i.get_stats_detailed()[y_stat]).strip("%").replace("∞", "inf")) for i in players if i.get_stats()["Rounds on Court"]])
        axis.scatter(xs, ys)
        a, b = np.polyfit(xs, ys, 1)
        axis.plot(xs, a*xs+b)
        fig.supxlabel(x_stat)
        fig.supylabel(y_stat)
        return fig

    # fixture related endpoints

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
    add_game_endpoints(app, comps)
    add_clip_endpoints(app, comps)
