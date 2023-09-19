import flask
from flask import request, send_file, render_template, Response, redirect

from structure.GameUtils import game_string_to_commentary
from tournaments.Tournament import Tournament
from util import get_console

app = flask.Flask(__name__)
app.config["DEBUG"] = True
con = get_console()

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
    con.info(f"Request for score: {request.json}")
    game_id = request.json["id"]
    ace = request.json["ace"]
    first_team = request.json["firstTeam"]
    first_player = request.json["firstPlayer"]
    competition.fixtures.get_game(game_id).teams[not first_team].score_point(first_player, ace)
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/ace')
def ace():
    con.info(f"Request for ace: {request.json}")
    game_id = request.json["id"]
    game = competition.fixtures.get_game(game_id)
    serving_team = game.teams[not game.first_team_serves]
    first_team = request.json["firstTeam"]
    competition.fixtures.get_game(game_id).teams[not first_team].score_point(serving_team.first_player_serves, True)
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/start')
def start():
    con.info(f"Request for start: {request.json}")
    game_id = request.json["id"]

    competition.fixtures.get_game(game_id).start(request.json["firstTeamServed"], request.json["swapTeamOne"],
                                                 request.json["swapTeamTwo"])
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/end')
def end():
    con.info(f"Request for end: {request.json}")
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).end(request.json["bestPlayer"])
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/timeout')
def timeout():
    con.info(f"Request for timeout: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).teams[not first_team].timeout()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/fault')
def fault():
    con.info(f"Request for fault: {request.json}")
    first_team = request.json["firstTeam"]
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).teams[not first_team].fault()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/undo')
def undo():
    con.info(f"Request for undo: {request.json}")
    game_id = request.json["id"]
    competition.fixtures.get_game(game_id).undo()
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


@app.post('/api/games/update/card')
def card():
    con.info(f"Request for card: {request.json}")
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


@app.get('/teams/')
def stats_directory_site():
    teams = [(i.name, i.nice_name()) for i in sorted(competition.teams, key=lambda a: a.nice_name())]
    return render_template("stats.html", teams=teams), 200


@app.get('/teams/<team_name>')
def stats_site(team_name):
    team = [i for i in competition.teams if team_name == i.nice_name()][0]
    recent_games = []
    for i in competition.fixtures.games_to_list():
        if team not in [j.team for j in i.teams] or not i.started:
            continue
        recent_games.append((repr(i) + f" ({i.score_string()})", i.id))

    players = [(i.name, [(k, v) for k, v in i.get_stats().items()]) for i in team.players]
    return render_template("each_team_stats.html", stats=[(k, v) for k, v in team.get_stats().items()],
                           teamName=team.name,
                           players=players, teamNameClean=team.nice_name(), recent_games=recent_games), 200


@app.get('/games/<game_id>/')
def game_site(game_id):
    if int(game_id) >= len(competition.fixtures.games_to_list()):
        raise Exception("Game Does not exist!!")
    game = competition.fixtures.get_game(int(game_id))
    teams = game.teams
    team_dicts = [i.get_stats() for i in teams]
    stats = [(i, *[j[i] for j in team_dicts]) for i in team_dicts[0]]
    best = game.best_player.tidy_name() if game.best_player else "TBD"
    players = [i for i in game.players()]
    roundNumber = game.round_number + 1
    if not game.started:
        status = "Waiting for toss"
    elif not game.game_ended():
        status = "Game in Progress"
    elif not game.best_player:
        status = "Finished"
    else:
        status = "Official"
    player_stats = [(i, *[j.get_stats()[i] for j in players]) for i in players[0].get_stats()]
    return render_template("game_page.html", game=game, status=status, players=[i.tidy_name() for i in players],
                           teams=teams, stats=stats, player_stats=player_stats, official=game.primary_official,
                           commentary=game_string_to_commentary(game), best=best, roundNumber=roundNumber), 200


@app.get('/ladder/')
def ladder_site():
    priority = {
        "Team Names": 1,
        "Games Played": 2,
        "Games Won": 1,
        "Games Lost": 3,
        "Green Cards": 5,
        "Yellow Cards": 4,
        "Red Cards": 4,
        "Faults": 5,
        "Timeouts Called": 5,
        "Points For": 5,
        "Points Against": 5,
        "Point Difference": 2,
    }
    teams = [(i.name, i.nice_name(), [(v, priority[k]) for k, v in i.get_stats().items()]) for i in
             sorted(competition.teams, key=lambda a: (-a.games_won, -(a.get_stats()["Point Difference"])))]
    headers = [(i, priority[i]) for i in (["Team Names"] + [i for i in competition.teams[0].get_stats()])]
    return render_template("ladder.html", headers=[(i - 1, k, v) for i, (k, v) in enumerate(headers)], teams=teams), 200


@app.get('/players/')
def players_site():
    priority = {
        "Name": 1,
        "B&F Votes": 1,
        "Points scored": 2,
        "Aces scored": 2,
        "Faults": 5,
        "Double Faults": 5,
        "Green Cards": 4,
        "Yellow Cards": 3,
        "Red Cards": 3,
        "Rounds on Court": 5,
        "Rounds Carded": 5,
    }
    all_players = []
    for i in sorted(competition.teams, key=lambda a: a.nice_name()):
        all_players += sorted(i.players, key=lambda a: a.name)
    print(all_players)
    players = [(i.name, i.team.nice_name(), [(v, priority[k]) for k, v in i.get_stats().items()]) for i in all_players]
    headers = ["Name"] + [i for i in competition.teams[0].players[0].get_stats()]
    return render_template("players.html", headers=[(i - 1, k, priority[k]) for i, k in enumerate(headers)],
                           players=players), 200


@app.get('/officials/<nice_name>/')
def official_site(nice_name):
    official = [i for i in competition.officials.officials if i.nice_name() == nice_name][0]
    recent_games = []
    for i in competition.fixtures.games_to_list():
        if official != i.primary_official:
            continue
        recent_games.append((f"Round {i.round_number + 1}: {repr(i)} ({i.score_string()})", i.id))
    return render_template("official.html", name=official.name, link=official.nice_name(),
                           stats=[(k, v) for k, v in official.get_stats().items()], games=recent_games), 200


@app.get('/officials/')
def official_directory_site():
    official = [(i, i.nice_name()) for i in competition.officials.officials]
    return render_template("all_officials.html", officials=official), 200


@app.get('/rules/')
def rules():
    return send_file("./resources/rules.pdf"), 200


@app.get('/log/')
def log():
    with open("./resources/latest.log", "r") as fp:
        return Response(fp.read(), mimetype='text/plain')


@app.get('/code_of_conduct/')
def code_of_conduct():
    return send_file("./resources/code_of_conduct.pdf"), 200

@app.get('/favicon.ico')
def icon():
    return send_file("static/favicon.ico")

@app.get('/games/<game_id>/edit')
def game_editor(game_id):
    if int(game_id) >= len(competition.fixtures.games_to_list()):
        raise Exception("Game Does not exist!!")
    game = competition.fixtures.get_game(int(game_id))
    teams = game.teams
    key = request.args.get("key", None)
    players = [i for i in game.players()]
    if key is None:
        return render_template("game_editor/no_access.html", error="You did not enter a password"), 403
    elif key not in [game.primary_official.key, "admin"]:
        return render_template("game_editor/no_access.html", error="The password you entered is not correct"), 403
    if not game.started:
        return render_template("game_editor/game_start.html", players=[i.tidy_name() for i in players],
                               teams=teams, game=game), 200
    elif not game.game_ended():
        return render_template("game_editor/edit_game.html", players=[i.tidy_name() for i in players],
                               teams=teams, game=game), 200
    elif not game.best_player or key == "admin":
        return render_template("game_editor/finalise.html", players=[i.tidy_name() for i in players],
                               teams=teams, game=game), 200
    else:
        return render_template("game_editor/game_done.html", error="This game has already been completed!"), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
