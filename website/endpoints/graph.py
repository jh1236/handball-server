import io

import numpy as np
from flask import request, Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as mtick
from structure.AllTournament import get_all_players, get_all_games


def colors(progress, m):
    top = (255, 0, 0)
    bottom = (0, 0, 255)
    r = (bottom[0] + (top[0] - bottom[0]) * (progress / m)) / 255
    g = (bottom[1] + (top[1] - bottom[1]) * (progress / m)) / 255
    b = (bottom[2] + (top[2] - bottom[2]) * (progress / m)) / 255
    return r, g, b


def make_graph(xs, ys, xLabel, yLabel):
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)

    if yLabel == "Frequency":
        yLabel = "Frequency (%)"
        if not (xs % 1 == 0).all():
            print((xs % 1 == 0))
            ax.hist(
                100. * xs / sum(xs),
                max(5, min(int((max(xs) - min(xs))), 20))
            )
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        else:
            xs, ys = np.unique(xs, return_counts=True)
            ax.bar(np.floor(xs), 100. * ys / np.sum(ys))
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    else:
        x_sort = np.sort(xs)
        y_sort = ys[np.argsort(xs)]
        freq = []
        for i, j in zip(x_sort, y_sort):
            freq.append(
                len([i for i1, j1 in zip(x_sort, y_sort) if i == i1 and j == j1])
            )
        if any(i != 1 for i in freq):
            m = max(freq)
            c_freq = [colors(i, m) for i in freq]
            ax.scatter(x_sort, y_sort, 300 * np.array(freq) / m, c=np.array(c_freq))
            # fig.delaxes(ax)
            # ax = fig.add_subplot(1,1,1, projection="3d")
            # _, _, baseline = ax.stem(x_sort,y_sort,freq)
            # baseline.remove()
            # ax.set_zlabel("Frequency")
        else:
            if xLabel == "Timeline" and yLabel == "Elo":
                ax.plot(x_sort, y_sort)
            ax.scatter(x_sort, y_sort)
            a, b = np.polyfit(xs, ys, 1)
            ax.plot(xs, a * xs + b)
    ax.set_xlabel(xLabel)
    ax.set_ylabel(yLabel)
    return fig


def add_graph_endpoints(app, comps):
    @app.get("/graphs/player")
    def plot_png():
        x = request.args.get("x", type=str)
        y = request.args.get("y", type=str)
        tournament = request.args.get("tournament", type=str, default=None)
        fig = players_per_tournament_graph(x, y, tournament)
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        return Response(output.getvalue(), mimetype="image/png")

    @app.get("/graphs/game_player")
    def player_plot_png():
        x = request.args.get("x", type=str)
        y = request.args.get("y", type=str)
        player = request.args.get("player", type=str, default=None)
        tournament = request.args.get("tournament", type=str, default=None)
        fig = games_per_player_graph(x, y, player, tournament)
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        return Response(output.getvalue(), mimetype="image/png")

    @app.get("/graphs/game")
    def games_plot_png():
        x = request.args.get("x", type=str)
        y = request.args.get("y", type=str)
        tournament = request.args.get("tournament", type=str, default=None)
        fig = games_per_tournament_graph(x, y, tournament)
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        return Response(output.getvalue(), mimetype="image/png")

    def games_per_player_graph(x_stat, y_stat, player, tournament):
        if tournament:
            players = [
                next(k for k in i.playing_players if k.nice_name() == player)
                for i in comps[tournament].games_to_list()
                if (not player or player in [j.nice_name() for j in i.playing_players])
                and (i.ranked or not (comps[tournament].details.get("ranked", True)))
            ]
        else:
            players = [
                next(k for k in i.playing_players if k.nice_name() == player)
                for i in get_all_games()
                if (not player or player in [j.nice_name() for j in i.playing_players])
                and i.ranked
            ]
        xs = np.array(
            [
                float(
                    str(i.get_stats_detailed().get(x_stat, 0))
                    .strip("%")
                    .replace("∞", "inf")
                )
                for i in players
                if i.get_stats()["Rounds Played"]
            ]
        )
        ys = np.array(
            [
                float(
                    str(i.get_stats_detailed().get(y_stat, 0))
                    .strip("%")
                    .replace("∞", "inf")
                )
                for i in players
                if i.get_stats()["Rounds Played"]
            ]
        )
        return make_graph(xs, ys, x_stat, y_stat)

    def players_per_tournament_graph(x_stat, y_stat, tournament):
        if tournament:
            players = [i for i in comps[tournament].players]
        else:
            players = [i for i in get_all_players()]
        xs = np.array(
            [
                float(
                    str(i.get_stats_detailed().get(x_stat, 0))
                    .strip("%")
                    .replace("∞", "inf")
                )
                for i in players
                if i.get_stats()["Rounds on Court"]
            ]
        )
        ys = np.array(
            [
                float(
                    str(i.get_stats_detailed().get(y_stat, 0))
                    .strip("%")
                    .replace("∞", "inf")
                )
                for i in players
                if i.get_stats()["Rounds on Court"]
            ]
        )
        return make_graph(xs, ys, x_stat, y_stat)

    def games_per_tournament_graph(x_stat, y_stat, tournament):
        if tournament:
            games = comps[tournament].games_to_list()
        else:
            games = get_all_games()
        xs = np.array(
            [
                float(str(i.get_stats().get(x_stat, 0)).strip("%").replace("∞", "inf"))
                for i in games
                if not i.bye
            ]
        )
        ys = np.array(
            [
                float(str(i.get_stats().get(y_stat, 0)).strip("%").replace("∞", "inf"))
                for i in games
                if not i.bye
            ]
        )
        return make_graph(xs, ys, x_stat, y_stat)
