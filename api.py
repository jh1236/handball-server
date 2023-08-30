import flask
from flask import request, send_file, render_template

import tournaments
from structure.Fixture import Fixture
from tournaments.Tournament import Tournament

app = flask.Flask(__name__)
app.config["DEBUG"] = True

competition: Tournament = tournaments.Swiss.load()
print(competition.teams)


@app.route('/api/teams', methods=['GET'])
def teams():
    return {i.name: i.as_map() for i in competition.teams}


@app.route('/api/games/current_round')
def current_games():
    return [i.to_map() for i in competition.rounds[-1] if not i.game.is_over()]


@app.route('/api/fixtures', methods=['GET'])
def fixtures():
    return [i.game.as_map() for i in competition.fixtures]


@app.route('/api/games/current', methods=['GET'])
def games():
    competition.save()
    return competition.current_game.as_map()


@app.route('/api/games/display', methods=['GET'])
def display():
    return competition.current_game.display_map()


@app.route('/api/games/update/score', methods=['POST'])
def score():
    print(request.json)
    c = request.json["ace"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    if first_team:
        competition.current_game.team_one.add_score(first_player, c)
    else:
        competition.current_game.team_two.add_score(first_player, c)
    competition.current_game.print_gamestate()
    return "", 204


@app.route('/api/games/update/start', methods=['POST'])
def start():
    print(request.json)

    competition.current_game.start(request.json["swap"], request.json["swapTeamOne"], request.json["swapTeamTwo"])
    competition.current_game.print_gamestate()
    return "", 204


@app.route('/api/games/update/end', methods=['POST'])
def end():
    print(request.json)
    competition.current_game.end(request.json["bestPlayer"])
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


@app.route('/api/games/update/undo', methods=['POST'])
def undo():
    print(request.json)
    competition.current_game.undo()
    competition.current_game.print_gamestate()
    return "", 204


@app.route('/api/games/update/card', methods=['POST'])
def card():
    print(request.json)
    color = request.json["color"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    if first_team:
        if color == "green":
            competition.current_game.team_one.green_card(first_player)
        elif color == "yellow":
            time = request.json["time"]
            competition.current_game.team_one.yellow_card(first_player, time)
        elif color == "red":
            competition.current_game.team_one.red_card(first_player)
    else:
        if color == "green":
            competition.current_game.team_two.green_card(first_player)
        elif color == "yellow":
            time = request.json["time"]
            competition.current_game.team_two.yellow_card(first_player, time)
        elif color == "red":
            competition.current_game.team_two.red_card(first_player)
    competition.current_game.print_gamestate()
    return "", 204


@app.route('/api/teams/image', methods=['GET'])
def image():
    team = request.args.get("name", type=str)
    return send_file(f"./resources/images/{team}.png", mimetype='image/png')


@app.route('/', methods=['GET'])
def site():
    fixtures = []
    for j in competition.fixtures:
        # print(j.fixture_to_table_row_2()) # for testing
        if isinstance(j, Fixture):
            fixtures.append(j.fixture_to_table_row())
        else:
            fixtures.append(j)

    return render_template("site.html", fixtures=fixtures), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
