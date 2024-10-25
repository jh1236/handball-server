import json
import os

from flask import jsonify, send_file
from flask import request

from database import db
from database.models import Tournaments
from structure import manage_game
from utils.logging_handler import logger
from utils.permissions import admin_only, officials_only

def add_tourney_endpoints(app):
    @app.post("/api/note")
    @admin_only
    def note():
        """
        SCHEMA:
        {
            tournament: str = the searchable name of the tournament
            note: str = the note for the tournament
        }
        """
        logger.info(f"Request for notes: {request.json}")
        tournament = request.json["tournament"]
        note = request.json["note"]
        t = Tournaments.query.filter(Tournaments.searchable_name == tournament).first()
        t.notes = note
        db.session.commit()
        return "", 204

    @app.get("/api/tournaments/image")
    def tourney_image():
        """
        SCHEMA:
        {
            name: str = the searchable name of the tournament
        }
        """
        tournament = request.args.get("name", type=str)
        if os.path.isfile(f"./resources/images/tournaments/{tournament}.png"):
            return send_file(
                f"./resources/images/tournaments/{tournament}.png", mimetype="image/png"
            )
        else:
            return send_file(
                f"./resources/images/teams/blank.png", mimetype="image/png"
            )

    @app.post("/api/tournaments/serve_style")
    @admin_only
    def serve_style():
        """
        WARNING: DO NOT CHANGE WHILE A GAME IS IN PROGRESS
        SCHEMA:
        {
            tournament: str = the searchable name of the tournament
            badminton_serves: bool = if the tournament should use badminton serving
        }
        """
        logger.info(f"Request for serve_style: {request.json}")
        tournament = request.json["tournament"]
        t = Tournaments.query.filter(Tournaments.searchable_name == tournament).first()
        t.badminton_serves = request.json.get("badminton_serves", not t.badminton_serves)
        db.session.commit()
        return "", 204

    @app.post("/api/games/update/create")
    @officials_only
    def create():
        """
        SCHEMA:
        {
            tournament: str = the searchable name of the tournament
            teamOne: str = the searchable name of the first team, or the name of the team to be created if players is populated
            teamTwo: str = the searchable name of the second team, or the name of the team to be created if players is populated
            official: str (OPTIONAL) = the searchable name of the official (used to change officials)
            scorer: str (OPTIONAL) = the searchable name of the scorer (used to change scorer)
            playersOne: list[str] (OPTIONAL) = the list of players' true name on team one if the game is created by players
            playersTwo: list[str] (OPTIONAL) = the list of players' true name on team two if the game is created by players
        }
        """
        logger.info(request.json)
        gid = manage_game.create_game(request.json["tournament"], request.json["teamOne"], request.json["teamTwo"],
                                      request.json["official"], request.json.get("playersOne", None),
                                      request.json.get("playersTwo", None))
        return jsonify({"id": gid})


    @app.post("/api/signup")
    def signup():
        """
        SCHEMA:
        {
            teamName: str = the name of the team to sign up
            playerOne: str = the name of the first player
            playerTwo: str [OPTIONAL] = the name of the second player. If not populated, the team is not added
            substitute: str [OPTIONAL] = the name of the team to substitute
            umpires: str = the list of people who wish to umpire for the tournament
        }
        """
        if request.json["playerTwo"]:
            with open("./config/signups/teams.json") as fp:
                teams = json.load(fp)
            if request.json["teamName"] in teams:
                return "Team already exists", 401
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
        logger.info(request.json["umpires"])
        with open("config/signups/officials.json", "w+") as fp:
            json.dump(umpires, fp)
        return "", 204
