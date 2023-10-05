import flask
from flask import request, send_file, render_template, Response, redirect

from Finals.BasicFinals import BasicFinals
from Finals.SecondChanceFinals import SecondChanceFinals
from tournaments.Fixtures import Fixtures
from tournaments.Swiss import Swiss
from website import init_api
from structure.GameUtils import game_string_to_commentary
from tournaments.Tournament import Tournament
from utils.logging_handler import logger, get_SUSS_handler

app = flask.Flask(__name__)
app.config["DEBUG"] = True
competition = Tournament(lambda a: Fixtures(a, Swiss(a).generate_round(), SecondChanceFinals(a).generate_round()))


# Team related endpoints
@app.get('/api/teams')
def teams():
    return {i.name: [j.name for j in i.players] for i in competition.teams}


@app.get('/api/teams/image')
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
    return [i.as_map() for i in competition.fixtures.games_to_list() if not i.best_player]


@app.get('/api/games/fixtures')
def all_fixtures():
    return [i.as_map() for i in competition.fixtures.games_to_list()]


@app.get('/api/games/display')
def display():
    game_id = int(request.args["id"])
    return competition.fixtures.get_game(game_id).display_map()


@app.get('/api/games/game')
def game():
    game_id = int(request.args["id"])
    return competition.fixtures.get_game(game_id).as_map()


# gameplay related endpoints

@app.post('/api/games/update/score')
def score():
    logger.info(f"Request for score: {request.json}")
    game_id = request.json["id"]
    ace = request.json["ace"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    competition.fixtures.get_game(game_id).teams[not first_team].score_point(first_player, ace)
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/ace')
def ace():
    logger.info(f"Request for ace: {request.json}")
    game_id = request.json["id"]
    game = competition.fixtures.get_game(game_id)
    serving_team = game.teams[not game.first_team_serves]
    first_team = request.json["firstTeam"]
    competition.fixtures.get_game(game_id).teams[not first_team].score_point(serving_team.first_player_serves, True)
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/start')
def start():
    logger.info(f"Request for start: {request.json}")
    game_id = request.json["id"]

    competition.fixtures.get_game(game_id).start(request.json["firstTeamServed"], request.json["swapTeamOne"],
                                                 request.json["swapTeamTwo"])
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/end')
def end():
    logger.info(f"Request for end: {request.json}")
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).end(request.json["bestPlayer"])
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/timeout')
def timeout():
    logger.info(f"Request for timeout: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).teams[not first_team].timeout()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/fault')
def fault():
    logger.info(f"Request for fault: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).teams[not first_team].fault()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/undo')
def undo():
    logger.info(f"Request for undo: {request.json}")
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).undo()
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/card')
def card():
    logger.info(f"Request for card: {request.json}")
    color = request.json["color"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    game_id = request.json["id"]
    if color == "green":
        competition.fixtures.get_game(game_id, ).teams[not first_team].green_card(first_player)
    elif color == "yellow":
        competition.fixtures.get_game(game_id).teams[not first_team].yellow_card(first_player, request.json["time"])
    elif color == "red":
        competition.fixtures.get_game(game_id).teams[not first_team].red_card(first_player)

    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


init_api(app, competition)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
