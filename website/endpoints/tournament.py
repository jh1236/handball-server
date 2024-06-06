import io
import json
import os
import time

from flask import request, send_file, jsonify

from structure import manageGame
from structure.AllTournament import get_all_players
from structure.Game import Game
from structure.Team import Team
from utils.logging_handler import logger
import numpy as np
from flask import request, send_file, Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure


def add_tourney_endpoints(app, comps):
    @app.post("/api/note")
    def note():
        tournament = request.json["tournament"]
        note = request.json["note"]
        if note == "del":
            comps[tournament].notes = ""
        else:
            comps[tournament].notes = note
        comps[tournament].save()
        return "", 204

    @app.get("/api/tournaments/image")
    def tourney_image():
        tournament = request.args.get("name", type=str)
        if os.path.isfile(f"./resources/images/tournaments/{tournament}.png"):
            return send_file(
                f"./resources/images/tournaments/{tournament}.png", mimetype="image/png"
            )
        else:
            return send_file(
                f"./resources/images/teams/blank.png", mimetype="image/png"
            )

    @app.get("/api/teams/stats")
    def stats():
        tournament = request.args.get("tournament", type=str)
        team_name = request.args.get("name", type=str)
        team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
        return team.get_stats(include_players=True)

    @app.get("/api/games/current_round")
    def current_round():
        tournament = request.args.get("tournament", type=str)
        return [
            i.as_map() for i in comps[tournament].games_to_list() if not i.best_player
        ]

    @app.get("/api/games/fixtures")
    def all_fixtures():
        tournament = request.args.get("tournament", type=str)
        return [i.as_map() for i in comps[tournament].games_to_list()]

    @app.get("/api/games/display")
    def display():
        tournament = request.args.get("tournament", type=str)
        game_id = int(request.args["id"])
        try:
            return comps[tournament].get_game(game_id).display_map()
        except ValueError:
            return {
                "leftTeam": {
                    "team": "TBD",
                    "score": 0,
                    "timeout": 0,
                    "players": ["None", "None"],
                    "captain": {
                        "name": "None",
                        "green": False,
                        "yellow": False,
                        "receivedYellow": False,
                        "red": False,
                        "serving": False,
                        "fault": False,
                        "cardPercent": 1,
                    },
                    "notCaptain": {
                        "name": "None",
                        "green": False,
                        "yellow": False,
                        "receivedYellow": False,
                        "red": False,
                        "serving": False,
                        "fault": False,
                        "cardPercent": 1,
                    },
                },
                "rightTeam": {
                    "team": "TBD",
                    "score": 0,
                    "timeout": 0,
                    "players": ["None", "None"],
                    "captain": {
                        "name": "None",
                        "green": False,
                        "yellow": False,
                        "receivedYellow": False,
                        "red": False,
                        "serving": False,
                        "fault": False,
                        "cardPercent": 1,
                    },
                    "notCaptain": {
                        "name": "None",
                        "green": False,
                        "yellow": False,
                        "receivedYellow": False,
                        "red": False,
                        "serving": False,
                        "fault": False,
                        "cardPercent": 1,
                    },
                },
                "rounds": 0,
                "umpire": "TBD",
                "court": "TBD",
            }

    @app.get("/api/games/game")
    def game():
        tournament = request.args.get("tournament", type=str)
        game_id = int(request.args["id"])
        return comps[tournament].get_game(game_id).as_map()

    @app.post("/api/games/update/create")
    def create():
        print(request.json)
        gid = manageGame.create_game(request.json["tournament"], request.json["teamOne"], request.json["teamTwo"],
                                     request.json["official"], request.json.get("playersOne", None), request.json.get("playersTwo", None))
        return jsonify({"id": gid})

    @app.post("/api/games/update/resolve")
    def resolve():
        tournament = request.json["tournament"]
        logger.info(f"Request for end: {request.json}")
        game_id = request.json["id"]
        comps[tournament].get_game(game_id).resolve()
        comps[tournament].save()
        return "", 204

    @app.post("/api/signup")
    def signup():
        if request.json["playerTwo"]:
            with open("./config/signups/teams.json") as fp:
                teams = json.load(fp)
            teams[request.json["teamName"]] = {
                "players": [
                    request.json["playerOne"],
                    request.json["playerTwo"],
                ],
                "colors": [
                    request.json["colorOne"],
                    request.json["colorTwo"],
                ],
            }
            if "substitute" in request.json and request.json["substitute"]:
                teams[request.json["teamName"]]["players"].append(
                    request.json["substitute"]
                )
            with open("./config/signups/teams.json", "w+") as fp:
                json.dump(teams, fp, indent=4, sort_keys=True)
        with open("config/signups/officials.json") as fp:
            umpires = json.load(fp)
        umpires += request.json["umpires"]
        print(request.json["umpires"])
        with open("config/signups/officials.json", "w+") as fp:
            json.dump(umpires, fp)
        for v in comps.values():
            v.initial_load()
            v.load()
        return "", 204
