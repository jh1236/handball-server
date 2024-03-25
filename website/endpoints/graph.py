import io

import numpy as np
from flask import request, Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as mtick
from matplotlib.pyplot import yticks
from werkzeug.datastructures import MultiDict

from structure.AllTournament import get_all_players, get_all_games
from structure.GameUtils import filter_games, get_query_descriptor


def colors(progress, m):
    top = (255, 0, 0)
    bottom = (0, 0, 255)
    r = (bottom[0] + (top[0] - bottom[0]) * (progress / m)) / 255
    g = (bottom[1] + (top[1] - bottom[1]) * (progress / m)) / 255
    b = (bottom[2] + (top[2] - bottom[2]) * (progress / m)) / 255
    return r, g, b


def to_number(x):
    intermediate: str = str(x).strip("%").replace("∞", "inf")
    if intermediate.replace(".", "").replace("-", "").isdecimal():
        return float(intermediate)
    return None


def make_graph(xs, ys, xLabel, yLabel):
    fig = Figure()
    ax = fig.add_subplot(1, 1, 1)
    x_sort = np.sort(xs)
    y_sort = ys[np.argsort(xs)]
    if "Length" == xLabel:
        y_sort = y_sort[x_sort > 0]
        x_sort = x_sort[x_sort > 0]
    if "Length" == yLabel:
        x_sort = x_sort[y_sort > 0]
        y_sort = y_sort[y_sort > 0]
    if yLabel == "Frequency":
        yLabel = "Frequency (%)"
        if not (x_sort % 1 == 0).all():
            ax.hist(
                100.0 * x_sort / sum(x_sort),
                max(5, min(int((max(x_sort) - min(x_sort))), 20)),
            )
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        else:
            x_sort, y_sort = np.unique(x_sort, return_counts=True)
            ax.bar(np.floor(x_sort), 100.0 * y_sort / np.sum(y_sort))
            ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    else:

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
            a, b = np.polyfit(x_sort, y_sort, 1)
            ax.plot(x_sort, a * x_sort + b)
    ax.set_xlabel(xLabel)
    ax.set_ylabel(yLabel)
    ax.set_ymargin(0.1)
    ax.set_title(yLabel + " by " + xLabel)
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

    @app.get("/graphs/game_player_by")
    def plot_png_by():
        x = request.args.get("x", type=str)
        y = request.args.get("y", type=str)
        args = MultiDict(request.args)
        del args["x"]
        del args["y"]
        fig = games_per_player_by(x, y, args)
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
                and not i.bye
            ]
        else:
            players = [
                next(k for k in i.playing_players if k.nice_name() == player)
                for i in get_all_games()
                if (not player or player in [j.nice_name() for j in i.playing_players])
                and (i.ranked)
                and not i.bye
            ]
        xs = np.array(
            [
                to_number(i.get_stats_detailed().get(x_stat, 0))
                for i in players
                if i.get_stats()["Rounds Played"]
            ]
        )
        ys = np.array(
            [
                to_number(i.get_stats_detailed().get(y_stat, 0))
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
                to_number(i.get_stats_detailed().get(x_stat, 0))
                for i in players
                if i.get_stats()["Rounds Played"]
            ]
        )
        ys = np.array(
            [
                to_number(i.get_stats_detailed().get(y_stat, 0))
                for i in players
                if i.get_stats()["Rounds Played"]
            ]
        )
        return make_graph(xs, ys, x_stat, y_stat)

    def games_per_tournament_graph(x_stat, y_stat, tournament):
        if tournament:
            games = comps[tournament].games_to_list()
        else:
            games = get_all_games()
        xs = np.array(
            [to_number(i.get_stats().get(x_stat, 0)) for i in games if not i.bye]
        )
        ys = np.array(
            [to_number(i.get_stats().get(y_stat, 0)) for i in games if not i.bye]
        )
        return make_graph(xs, ys, x_stat, y_stat)

    def games_per_player_by(x_stat, y_stat, args):
        players = []
        games, details = filter_games(get_all_games(), args, get_details=True)
        for game, game_players in games:
            players += [i for i in game.all_players if i.nice_name() in game_players]
        player = (
            [i.strip("~") for i in args.getlist("Player") if i.startswith("~")] + [None]
        )[0]
        out = {}
        for i in players:
            out[i.get_game_details()[x_stat]] = out.get(
                i.get_game_details()[x_stat], []
            ) + [to_number(i.get_stats_detailed()[y_stat])]
        xs = [to_number(i) for i in sorted(out.keys())]
        if any(i is None for i in xs):
            xs = [str(i) for i in sorted(out.keys())]
        else:
            xs = np.array(xs)
        ys = np.array([(1.0 * sum(out[i])) / len(out[i]) for i in sorted(out.keys())])
        if "Length" == x_stat:
            ys = ys[xs > 0]
            xs = xs[xs > 0]
        if "Length" == y_stat:
            xs = xs[ys > 0]
            ys = ys[ys > 0]
        if "Elo" == y_stat:
            ys = ys - 1500
        fig = Figure(figsize=(8, 6))  # figsize=(12,12)
        ax = fig.add_subplot(1, 1, 1)

        a = ax.bar(xs, ys, 0.6)
        if "Elo" == y_stat:
            ax.bar_label(
                a, labels=[f"{round(i + 1500)}" for i in ys], label_type="center"
            )
            locs = ax.get_yticks()
            ax.set_yticks(locs, map(lambda x: f"{x + 1500}", locs))
        else:
            ax.bar_label(
                a,
                labels=[f"{round(i, 2)}" for i in ys],
                label_type="edge",
                rotation=45 * (len(xs) >= 10),
            )
        if isinstance(xs[0], str):
            xticks = ax.get_xticks()
            ax.set_xticks(xticks, [i.replace(" ", "\n") for i in xs])
        ax.set_xlabel(x_stat)
        ax.set_ylabel(y_stat + " Per Game")
        sub_title = get_query_descriptor(details)
        if sub_title:
            ax.set_title(sub_title,fontsize = 7, style = "italic")
        fig.suptitle(
            y_stat
            + " by "
            + x_stat
            + (f" for {(player).replace('_',' ').title()}" if player else ""),
            fontsize = 15
        )
        return fig
