import os
import time

import flask
from flask import request, send_file, jsonify

from structure.Game import Game
from structure.Team import Team
from structure.Tournament import load_all_tournaments
from utils.logging_handler import logger
import json

from website.website import init_api

app = flask.Flask(__name__)
app.config["DEBUG"] = True
comps = load_all_tournaments()

with open("./config/password.txt", "r") as fp:
    admin_password = fp.read()


# Team related endpoints
@app.get("/api/teams")
def teams():
    tournament = request.args.get("tournament", type=str)
    return {i.name: [j.name for j in i.players] for i in comps[tournament].teams}


@app.get("/api/tournaments")
def tournaments():
    return list(comps.values())


@app.post("/api/note")
def note():
    tournament = request.json["tournament"]
    note = request.json["note"]
    if note == "del":
        comps[tournament].notes = ""
    else:
        comps[tournament].notes = note
    return "", 204


@app.get("/api/teams/image")
def team_image():
    team = request.args.get("name", type=str)
    if os.path.isfile(f"./resources/images/teams/{team}.png"):
        return send_file(f"./resources/images/teams/{team}.png", mimetype="image/png")
    return send_file("./resources/images/teams/blank.png", mimetype="image/png")


@app.get("/api/tournaments/image")
def tourney_image():
    tournament = request.args.get("name", type=str)
    if os.path.isfile(f"./resources/images/tournaments/{tournament}.png"):
        return send_file(
            f"./resources/images/tournaments/{tournament}.png", mimetype="image/png"
        )
    else:
        return send_file(f"./resources/images/teams/blank.png", mimetype="image/png")


@app.get("/api/image")
def image():
    team = request.args.get("name", type=str)
    return send_file(f"./resources/images/{team}.png", mimetype="image/png")


@app.get("/api/teams/stats")
def stats():
    tournament = request.args.get("tournament", type=str)
    team_name = request.args.get("name", type=str)
    team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
    return team.get_stats(include_players=True)


# fixture related endpoints


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


@app.get("/api/games/change_code")
def change_code():
    tournament = request.args.get("tournament", type=str)
    game_id = int(request.args["id"])
    return jsonify({"code": comps[tournament].get_game(game_id).update_count})


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


# gameplay related endpoints


@app.post("/api/games/update/score")
def score():
    tournament = request.json["tournament"]
    logger.info(f"Request for score: {request.json}")
    game_id = request.json["id"]
    ace = request.json["ace"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    comps[tournament].get_game(game_id).teams[not first_team].score_point(
        first_player, ace
    )
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/substitute")
def substitute():
    tournament = request.json["tournament"]
    logger.info(f"Request for score: {request.json}")
    game_id = request.json["id"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    comps[tournament].get_game(game_id).teams[not first_team].sub_player(first_player)
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/ace")
def ace():
    tournament = request.json["tournament"]
    logger.info(f"Request for ace: {request.json}")
    game_id = request.json["id"]
    game = comps[tournament].get_game(game_id)
    first_team = request.json.get("firstTeam", game.teams[0].serving)
    game.teams[not first_team].score_point(None, True)
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/start")
def start():
    tournament = request.json["tournament"]
    logger.info(f"Request for start: {request.json}")
    game_id = request.json["id"]

    comps[tournament].get_game(game_id).start(
        request.json["firstTeamServed"],
        request.json["swapTeamOne"],
        request.json["swapTeamTwo"],
    )
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/round")
def new_round():
    tournament = comps[request.json["tournament"]]
    tournament.update_games(True)
    tournament.update_games()
    tournament.save()
    return "", 200


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
            players += [j for j in tournament.players if j.nice_name() == i]

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
            players += [j for j in tournament.players if j.nice_name() == i]
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
    return jsonify({"id": g.id}), 204


@app.post("/api/games/update/end")
def end():
    tournament = request.json["tournament"]
    logger.info(f"Request for end: {request.json}")
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).end(
        request.json["bestPlayer"],
        request.json.get("cards", None),
        request.json.get("notes", None),
    )
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/protest")
def protest():
    tournament = request.json["tournament"]
    logger.info(f"Request for end: {request.json}")
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).protest(
        request.json["teamOne"], request.json["teamTwo"]
    )
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/resolve")
def resolve():
    tournament = request.json["tournament"]
    logger.info(f"Request for end: {request.json}")
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).resolve()
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/timeout")
def timeout():
    tournament = request.json["tournament"]
    logger.info(f"Request for timeout: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).teams[not first_team].timeout()
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/forfeit")
def forfeit():
    tournament = request.json["tournament"]
    logger.info(f"Request for forfeit: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).teams[not first_team].forfeit()
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/endTimeout")
def end_timeout():
    tournament = request.json["tournament"]
    logger.info(f"Request for endTimeout: {request.json}")
    game_id = request.json["id"]
    [i.end_timeout() for i in comps[tournament].get_game(game_id).teams]
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/serve_clock")
def serve_timer():
    tournament = request.json["tournament"]
    logger.info(f"Request for timeout: {request.json}")
    game_id = request.json["id"]
    if request.json["start"]:
        comps[tournament].get_game(game_id)._serve_clock = time.time()
    else:
        comps[tournament].get_game(game_id)._serve_clock = -1
    comps[tournament].get_game(game_id).update_count += 1
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/fault")
def fault():
    tournament = request.json["tournament"]
    logger.info(f"Request for fault: {request.json}")
    first_team = request.json.get("firstTeam", None)
    game_id = request.json["id"]
    if first_team is None:
        first_team = comps[tournament].get_game(game_id).teams[0].serving
    comps[tournament].get_game(game_id).teams[not first_team].fault()
    comps[tournament].save()
    return "", 204


@app.post("/api/games/update/undo")
def undo():
    tournament = request.json["tournament"]
    logger.info(f"Request for undo: {request.json}")
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).undo()
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


@app.post("/api/games/update/card")
def card():
    tournament = request.json["tournament"]
    logger.info(f"Request for card: {request.json}")
    color = request.json["color"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    game_id = request.json["id"]
    time = request.json["time"]
    if time < 3:
        time += 10
    if color == "green":
        comps[tournament].get_game(game_id,).teams[
            not first_team
        ].green_card(first_player)
    elif color == "yellow":
        comps[tournament].get_game(game_id).teams[not first_team].yellow_card(
            first_player, time
        )
    elif color == "red":
        comps[tournament].get_game(game_id).teams[not first_team].red_card(first_player)

    comps[tournament].get_game(game_id).print_gamestate()
    comps[tournament].save()
    return "", 204


init_api(app, comps)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
