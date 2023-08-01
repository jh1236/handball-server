import json

import flask
from flask import request

import tournaments
from structure.Team import Team

app = flask.Flask(__name__)
app.config["DEBUG"] = True

with open("G:/Programming/python/HandballAPI/resources/teamsClean.json") as fp:
    team_list = [Team.from_map(k, v) for k, v in json.load(fp).items()]
competition = tournaments.rr(team_list)


@app.route('/api/teams', methods=['GET'])
def teams():
    print({i.name: i.as_map() for i in team_list[0:1]})
    return {i.name: i.as_map() for i in team_list}


@app.route('/api/games/current', methods=['GET'])
def games():
    return competition.current_game.as_map()


@app.route('/api/games/update', methods=['POST'])
def post_test():
    print(request.json)
    with open("G:/Programming/python/HandballAPI/resources/games.json") as fp:
        games = json.load(fp)
    games[-1] = request.json
    print(games)
    with open("G:/Programming/python/HandballAPI/resources/games.json", "w") as fp:
        json.dump(games, fp)
    return "", 204


@app.route('/api/games/update/score', methods=['POST'])
def score():
    print(request.json)
    c = request.json["ace"]
    first_team = request.json["firstTeam"]
    left_player = request.json["leftPlayer"]
    if first_team:
        competition.current_game.team_one.add_score(left_player, c)
    else:
        competition.current_game.team_two.add_score(left_player, c)
    competition.current_game.print_gamestate()
    return "", 204


@app.route('/api/games/update/timeout', methods=['POST'])
def timeout():
    print(request.json)
    first_team = request.json["firstTeam"]
    if first_team:
        competition.current_game.team_one.call_timeout()
    else:
        competition.current_game.team_two.call_timeout()
    competition.current_game.print_gamestate()
    return "", 204


@app.route('/api/games/update/card', methods=['POST'])
def card():
    print(request.json)
    color = request.json["color"]
    first_team = request.json["firstTeam"]
    left_player = request.json["leftPlayer"]
    if first_team:
        if color == "green":
            competition.current_game.team_one.green_card(left_player)
        elif color == "yellow":
            competition.current_game.team_one.yellow_card(left_player)
        elif color == "red":
            competition.current_game.team_one.red_card(left_player)
    else:
        if color == "green":
            competition.current_game.team_two.green_card(left_player)
        elif color == "yellow":
            competition.current_game.team_two.yellow_card(left_player)
        elif color == "red":
            competition.current_game.team_two.red_card(left_player)
    competition.current_game.print_gamestate()
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
