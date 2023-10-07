import random

from flask import render_template, send_file, request, Response

from structure.GameUtils import game_string_to_commentary
from utils.logging_handler import logger


def init_api(app, competition):
    @app.get('/')
    def site():
        fixtures = [(n, [i.fixture_to_table_row() for i in j]) for n, j in enumerate(competition.fixtures)]
        finals = [(n, [i.fixture_to_table_row() for i in j]) for n, j in enumerate(competition.finals)]
        return render_template("site.html", fixtures=fixtures, finals=finals), 200

    @app.get('/teams/')
    def stats_directory_site():
        teams = [(i.name, i.nice_name()) for i in sorted(competition.teams, key=lambda a: a.nice_name())]
        return render_template("stats.html", teams=teams), 200

    @app.get('/teams/<team_name>')
    def stats_site(team_name):
        team = [i for i in competition.teams if team_name == i.nice_name()][0]
        recent_games = []
        for i in competition.games_to_list():
            if team not in [j.team for j in i.teams] or not i.started:
                continue
            recent_games.append((repr(i) + f" ({i.score_string()})", i.id))

        players = [(i.name, [(k, v) for k, v in i.get_stats().items()]) for i in team.players]
        return render_template("each_team_stats.html", stats=[(k, v) for k, v in team.get_stats().items()],
                               teamName=team.name,
                               players=players, teamNameClean=team.nice_name(), recent_games=recent_games), 200

    @app.get('/games/<game_id>/')
    def game_site(game_id):
        if int(game_id) >= len(competition.games_to_list()):
            raise Exception("Game Does not exist!!")
        game = competition.get_game(int(game_id))
        teams = game.teams
        team_dicts = [i.get_stats() for i in teams]
        stats = [(i, *[j[i] for j in team_dicts]) for i in team_dicts[0]]
        best = game.best_player.tidy_name() if game.best_player else "TBD"
        players = game.players()
        round_number = game.round_number + 1
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
                               commentary=game_string_to_commentary(game), best=best, roundNumber=round_number), 200

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
            "ELO": 3
        }
        teams = [(i.name, i.nice_name(), [(v, priority[k]) for k, v in i.get_stats().items()]) for i in
                 sorted(competition.teams, key=lambda a: (-a.games_won, -(a.get_stats()["Point Difference"])))]
        headers = [(i, priority[i]) for i in (["Team Names"] + [i for i in competition.teams[0].get_stats()])]
        return render_template("ladder.html", headers=[(i - 1, k, v) for i, (k, v) in enumerate(headers)],
                               teams=teams), 200

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
        players = [(i.name, i.team.nice_name(), [(v, priority[k]) for k, v in i.get_stats().items()]) for i in
                   all_players]
        headers = ["Name"] + [i for i in competition.teams[0].players[0].get_stats()]
        return render_template("players.html", headers=[(i - 1, k, priority[k]) for i, k in enumerate(headers)],
                               players=players), 200

    @app.get('/officials/<nice_name>/')
    def official_site(nice_name):
        official = [i for i in competition.officials.officials if i.nice_name() == nice_name][0]
        recent_games = []
        for i in competition.games_to_list():
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

    @app.get('/admin/log/')
    def admin():
        key = request.args.get("key", None)
        if key is None:
            return render_template("game_editor/no_access.html", error="You did not enter a password"), 403
        elif key != "admin":
            return render_template("game_editor/no_access.html", error="The password you entered is not correct"), 403
        with open("./resources/latest.log", "r") as fp:
            return Response(fp.read(), mimetype='text/plain')

    @app.get('/admin/')
    def log():
        key = request.args.get("key", None)
        if key is None:
            return render_template("game_editor/no_access.html", error="You did not enter a password"), 403
        elif key != "admin":
            return render_template("game_editor/no_access.html", error="The password you entered is not correct"), 403
        return render_template("admin.html"), 200

    @app.get('/code_of_conduct/')
    def code_of_conduct():
        rand = random.Random()
        if rand.randrange(0, 10):
            return send_file("./resources/code_of_conduct_2.pdf"), 200
        return send_file("./resources/code_of_conduct.pdf"), 200

    @app.get('/favicon.ico')
    def icon():
        return send_file("static/favicon.ico")

    @app.get('/games/<game_id>/edit')
    def game_editor(game_id):
        if int(game_id) >= len(competition.games_to_list()):
            raise Exception("Game Does not exist!!")
        game = competition.get_game(int(game_id))
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
