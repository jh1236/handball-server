import logging
import os

import flask
from flask import request, send_file, jsonify

from structure.Game import Game
from structure.Player import Player
from structure.Team import Team
from structure.Tournament import load_all_tournaments
from utils.logging_handler import logger
from website import init_api

logger.setLevel(logging.CRITICAL)
app = flask.Flask(__name__)
app.config["DEBUG"] = True
comps = load_all_tournaments()


with open("./config/password.txt", "r") as fp:
    admin_password = fp.read()


# Team related endpoints
@app.get('/api/teams')
def teams():
    tournament = request.args.get("tournament", type=str)
    return {i.name: [j.name for j in i.players] for i in comps[tournament].teams}


@app.get('/api/tournaments')
def tournaments():
    return list(comps.values())


@app.post('/api/tournaments/note')
def note():
    tournament = request.args.get("tournament", type=str)
    note = request.args.get("note", type=str)
    if note == "del":
        comps[tournament].notes = []
    else:
        comps[tournament].notes.append(note)
    return "", 204


@app.get('/api/teams/image')
def team_image():
    team = request.args.get("name", type=str)
    if os.path.isfile(f"./resources/images/teams/{team}.png"):
        return send_file(f"./resources/images/teams/{team}.png", mimetype='image/png')
    else:
        return send_file(f"./resources/images/teams/blank.png", mimetype='image/png')


@app.get('/api/tournaments/image')
def tourney_image():
    tournament = request.args.get("name", type=str)
    if os.path.isfile(f"./resources/images/tournaments/{tournament}.png"):
        return send_file(f"./resources/images/tournaments/{tournament}.png", mimetype='image/png')
    else:
        return send_file(f"./resources/images/teams/blank.png", mimetype='image/png')


@app.get('/api/image')
def image():
    team = request.args.get("name", type=str)
    return send_file(f"./resources/images/{team}.png", mimetype='image/png')


@app.get('/api/teams/stats')
def stats():
    tournament = request.args.get("tournament", type=str)
    team_name = request.args.get("name", type=str)
    team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
    return team.get_stats(include_players=True)


# fixture related endpoints

@app.get('/api/games/current_round')
def current_round():
    tournament = request.args.get("tournament", type=str)
    return [i.as_map() for i in comps[tournament].games_to_list() if not i.best_player]


@app.get('/api/games/fixtures')
def all_fixtures():
    tournament = request.args.get("tournament", type=str)
    return [i.as_map() for i in comps[tournament].games_to_list()]


@app.get('/api/games/display')
def display():
    tournament = request.args.get("tournament", type=str)
    game_id = int(request.args["id"])
    return comps[tournament].get_game(game_id).display_map()


@app.get('/api/games/game')
def game():
    tournament = request.args.get("tournament", type=str)
    game_id = int(request.args["id"])
    return comps[tournament].get_game(game_id).as_map()


# testing related endpoints
@app.get('/api/mirror')
def mirror():
    logger.info(f"Request for score: {request.args}")
    d = dict(request.args)
    if not d:
        d = {
            "All these webs on me": " You think I'm Spiderman",
            "Shout out": "martin luther King",
            "this is the sound of a robot": "ELELALAELE-BING-ALELILLELALE"
        }
    return str(d), 200


# gameplay related endpoints

@app.post('/api/games/update/score')
def score():
    tournament = request.json["tournament"]
    logger.info(f"Request for score: {request.json}")
    game_id = request.json["id"]
    ace = request.json["ace"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    comps[tournament].get_game(game_id).teams[not first_team].score_point(first_player, ace)
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/ace')
def ace():
    tournament = request.json["tournament"]
    logger.info(f"Request for ace: {request.json}")
    game_id = request.json["id"]
    first_team = request.json["firstTeam"]
    comps[tournament].get_game(game_id).teams[not first_team].score_point(None, True)
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/start')
def start():
    tournament = request.json["tournament"]
    logger.info(f"Request for start: {request.json}")
    game_id = request.json["id"]

    comps[tournament].get_game(game_id).start(request.json["firstTeamServed"], request.json["swapTeamOne"],
                                              request.json["swapTeamTwo"])
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/create')
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
        tournament.add_team(team_one)
    else:
        team_one = [i for i in tournament.teams if request.json["teamOne"] in [i.nice_name(), i.name]][0]
    if "playersTwo" in request.json:
        players = []
        for i in request.json["playersTwo"]:
            players += [j for j in tournament.players() if j.nice_name() == i]
        team_two = Team.find_or_create(tournament, request.json["teamTwo"], players)
        tournament.add_team(team_two)
    else:
        team_two = [i for i in tournament.teams if request.json["teamTwo"] in [i.nice_name(), i.name]][0]
    official = [i for i in tournament.officials if request.json["official"] in [i.nice_name(), i.name]][0]
    g = Game(team_one, team_two, tournament)
    g.court = 0
    if official:
        g.set_primary_official(official)
    tournament.fixtures[-1][0] = g
    tournament.update_games()
    tournament.save()
    return "", 204


@app.post('/api/games/update/end')
def end():
    tournament = request.json["tournament"]
    logger.info(f"Request for end: {request.json}")
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).end(request.json["bestPlayer"])
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/timeout')
def timeout():
    tournament = request.json["tournament"]
    logger.info(f"Request for timeout: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).teams[not first_team].timeout()
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/endTimeout')
def end_timeout():
    tournament = request.json["tournament"]
    logger.info(f"Request for endTimeout: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).teams[not first_team].in_timeout = False
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/fault')
def fault():
    tournament = request.json["tournament"]
    logger.info(f"Request for fault: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).teams[not first_team].fault()
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/undo')
def undo():
    tournament = request.json["tournament"]
    logger.info(f"Request for undo: {request.json}")
    game_id = request.json["id"]
    comps[tournament].get_game(game_id).undo()
    comps[tournament].get_game(game_id).print_gamestate()
    comps[tournament].save()
    return "", 204


@app.post('/api/games/update/card')
def card():
    tournament = request.json["tournament"]
    logger.info(f"Request for card: {request.json}")
    color = request.json["color"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    game_id = request.json["id"]
    if color == "green":
        comps[tournament].get_game(game_id, ).teams[not first_team].green_card(first_player)
    elif color == "yellow":
        comps[tournament].get_game(game_id).teams[not first_team].yellow_card(first_player, request.json["time"])
    elif color == "red":
        comps[tournament].get_game(game_id).teams[not first_team].red_card(first_player)

    comps[tournament].get_game(game_id).print_gamestate()
    comps[tournament].save()
    return "", 204


init_api(app, comps)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
