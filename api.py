import flask
from flask import request, send_file, render_template, Response

from tournaments.Tournament import Tournament

app = flask.Flask(__name__)
app.config["DEBUG"] = True

competition = Tournament()


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
    return [i.as_map() for i in competition.fixtures.rounds[-1]]


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


# website related endpoints

@app.get('/')
def site():
    fixtures = [(n, [i.fixture_to_table_row() for i in j]) for n, j in enumerate(competition.fixtures.rounds)]
    return render_template("site.html", fixtures=fixtures), 200


@app.get('/stats/')
def stats_directory_site():
    teams = [(i.name, i.nice_name()) for i in competition.teams]
    return render_template("stats.html", teams=teams), 200


@app.get('/stats/<team_name>')
def stats_site(team_name):
    team = [i for i in competition.teams if team_name == i.nice_name()][0]
    players = [(i.name, [(k, v) for k, v in i.get_stats().items()]) for i in team.players]
    return render_template("each_team_stats.html", stats=[(k, v) for k, v in team.get_stats().items()],
                           teamName=team.name,
                           players=players, teamNameClean=team.nice_name()), 200


@app.get('/game/<game_id>')
def game_site(game_id):
    game = competition.fixtures.get_game(int(game_id))
    teams = game.teams
    team_dicts = [i.get_stats() for i in teams]
    stats = [(i, *[j[i] for j in team_dicts]) for i in team_dicts[0]]
    players = [i for i in game.players()]
    player_stats = [(i, *[j.get_stats()[i] for j in players]) for i in players[0].get_stats()]
    return render_template("game_page.html", players=[i.tidy_name() for i in players],
                           teams=teams, stats=stats, player_stats=player_stats, official=game.primary_official), 200


@app.get('/ladder/')
def ladder_site():
    teams = [(i.name, i.nice_name(), [(k, v) for k, v in i.get_stats().items()]) for i in
             sorted(competition.teams, key=lambda a: (-a.games_won, -(a.get_stats()["Point Difference"])))]
    headers = [
        "Team Name",
        "Games Played",
        "Games Won",
        "Games Lost",
        "Points For",
        "Points Against",
        "Point Difference",
    ]
    return render_template("ladder.html", headers=headers, teams=teams), 200


@app.get('/rules/')
def rules():
    return send_file("./resources/rules.pdf"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
