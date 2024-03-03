import io
import json
import os

from flask import request, send_file

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
            return send_file(f"./resources/images/teams/blank.png", mimetype="image/png")
    @app.get("/api/teams/stats")
    def stats():
        tournament = request.args.get("tournament", type=str)
        team_name = request.args.get("name", type=str)
        team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
        return team.get_stats(include_players=True)

    @app.get("/api/games/current_round")
    def current_round():
        tournament = request.args.get("tournament", type=str)
        return [i.as_map() for i in comps[tournament].games_to_list() if not i.best_player]


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
        tournament = comps[request.json["tournament"]]
        if not tournament.fixtures_class.manual_allowed():
            return "Not Allowed", 403
        if any([not (i.best_player or i.bye) for i in tournament.games_to_list()]):
            return "Not Allowed", 403
        if "playersOne" in request.json:
            players = []
            for i in request.json["playersOne"]:
                players += [j for j in tournament.players() if j.nice_name() == i]

            team_one = Team.find_or_create(tournament, request.json["teamOne"], players)
            if team_one not in tournament.teams:
                tournament.add_team(team_one)
        else:
            team_one = [
                i
                for i in tournament.teams
                if request.json["teamOne"] in [i.nice_name(), i.name]
            ][0]
        if "playersTwo" in request.json:
            players = []
            for i in request.json["playersTwo"]:
                players += [j for j in tournament.players() if j.nice_name() == i]
            team_two = Team.find_or_create(tournament, request.json["teamTwo"], players)
            if team_two not in tournament.teams:
                tournament.add_team(team_two)
        else:
            team_two = [
                i
                for i in tournament.teams
                if request.json["teamTwo"] in [i.nice_name(), i.name]
            ][0]
        official = [
            i
            for i in tournament.officials
            if request.json["official"] in [i.nice_name(), i.name]
        ][0]
        g = Game(team_one, team_two, tournament)
        g.court = 0
        if official:
            g.set_primary_official(official)
        tournament.fixtures[-1][-1] = g
        tournament.update_games()
        tournament.save()
        return "", 204




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
