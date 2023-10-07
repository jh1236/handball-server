import flask
from flask import request, send_file

from structure.Tournament import Tournament
from tournaments.SecondChanceFinals import SecondChanceFinals
from tournaments.Swiss import Swiss
from utils.logging_handler import logger
from website import init_api

app = flask.Flask(__name__)
app.config["DEBUG"] = True
competition = Tournament("games.json", Swiss, SecondChanceFinals)


# Team related endpoints
@app.get('/api/teams')
def teams():
    return {i.name: [j.name for j in i.players] for i in competition.teams}


@app.get('/api/teams/image')
def team_image():
    team = request.args.get("name", type=str)
    return send_file(f"./resources/images/teams/{team}.png", mimetype='image/png')


@app.get('/api/image')
def image():
    team = request.args.get("name", type=str)
    return send_file(f"./resources/images/{team}.png", mimetype='image/png')


@app.get('/api/teams/stats')
def stats():
    team_name = request.args.get("name", type=str)
    team = [i for i in competition.teams if team_name == i.nice_name()][0]
    return team.get_stats(include_players=True)


# fixture related endpoints

@app.get('/api/games/current_round')
def current_round():
    return [i.as_map() for i in competition.games_to_list() if not i.best_player]


@app.get('/api/games/fixtures')
def all_fixtures():
    return [i.as_map() for i in competition.games_to_list()]


@app.get('/api/games/display')
def display():
    game_id = int(request.args["id"])
    return competition.get_game(game_id).display_map()


@app.get('/api/games/game')
def game():
    game_id = int(request.args["id"])
    return competition.get_game(game_id).as_map()


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
    logger.info(f"Request for score: {request.json}")
    game_id = request.json["id"]
    ace = request.json["ace"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    competition.get_game(game_id).teams[not first_team].score_point(first_player, ace)
    competition.save()
    return "", 204


@app.post('/api/games/update/ace')
def ace():
    logger.info(f"Request for ace: {request.json}")
    game_id = request.json["id"]
    game = competition.get_game(game_id)
    serving_team = game.teams[not game.first_team_serves]
    first_team = request.json["firstTeam"]
    competition.get_game(game_id).teams[not first_team].score_point(serving_team.first_player_serves, True)
    competition.save()
    return "", 204


@app.post('/api/games/update/start')
def start():
    logger.info(f"Request for start: {request.json}")
    game_id = request.json["id"]

    competition.get_game(game_id).start(request.json["firstTeamServed"], request.json["swapTeamOne"],
                                        request.json["swapTeamTwo"])
    competition.save()
    return "", 204


@app.post('/api/games/update/end')
def end():
    logger.info(f"Request for end: {request.json}")
    game_id = request.json["id"]
    competition.get_game(game_id).end(request.json["bestPlayer"])
    competition.save()
    return "", 204


@app.post('/api/games/update/timeout')
def timeout():
    logger.info(f"Request for timeout: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    competition.get_game(game_id).teams[not first_team].timeout()
    competition.save()
    return "", 204


@app.post('/api/games/update/fault')
def fault():
    logger.info(f"Request for fault: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    competition.get_game(game_id).teams[not first_team].fault()
    competition.save()
    return "", 204


@app.post('/api/games/update/undo')
def undo():
    logger.info(f"Request for undo: {request.json}")
    game_id = request.json["id"]
    competition.get_game(game_id).undo()
    competition.get_game(game_id).print_gamestate()
    competition.save()
    return "", 204


@app.post('/api/games/update/card')
def card():
    logger.info(f"Request for card: {request.json}")
    color = request.json["color"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    game_id = request.json["id"]
    if color == "green":
        competition.get_game(game_id, ).teams[not first_team].green_card(first_player)
    elif color == "yellow":
        competition.get_game(game_id).teams[not first_team].yellow_card(first_player, request.json["time"])
    elif color == "red":
        competition.get_game(game_id).teams[not first_team].red_card(first_player)

    competition.get_game(game_id).print_gamestate()
    competition.save()
    return "", 204


init_api(app, competition)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
