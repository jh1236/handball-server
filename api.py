import flask
from flask import request, send_file, render_template, Response

from tournaments.Tournament import Tournament

app = flask.Flask(__name__)
app.config["DEBUG"] = True

competition = Tournament()


@app.get('/api/teams')
def teams():
    return {i.name: [j.name for j in i.players] for i in competition.teams}


@app.get('/api/current_round')
def current_round():
    return [i.as_map() for i in competition.fixtures.rounds[-1]]


@app.get('/api/fixtures')
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


@app.post('/api/games/update/score')
def score():
    print(request.json)
    game_id = request.json["id"]
    ace = request.json["ace"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    competition.fixtures.get_game(game_id).teams[not first_team].score_point(first_player, ace)
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/start')
def start():
    print(request.json)
    game_id = request.json["id"]

    competition.fixtures.get_game(game_id).start(request.json["firstTeamServed"], request.json["swapTeamOne"],
                                                 request.json["swapTeamTwo"])
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/end')
def end():
    print(request.json)
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).end(request.json["bestPlayer"])
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/timeout')
def timeout():
    print(request.json)
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).teams[not first_team].timeout()
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/undo')
def undo():
    print(request.json)
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).undo()
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/card')
def card():
    print(request.json)
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


@app.get('/api/teams/image')
def image():
    team = request.args.get("name", type=str)
    return send_file(f"./resources/images/{team}.png", mimetype='image/png')


@app.get('/')
def site():
    fixtures = []
    for j in competition.fixtures.games_to_list():
        # print(j.fixture_to_table_row_2()) # for testing
        fixtures.append(j.fixture_to_table_row())

    return render_template("site.html", fixtures=fixtures), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
