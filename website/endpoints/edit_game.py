import time

from flask import request, jsonify

from utils.logging_handler import logger


def add_game_endpoints(app, comps):
    @app.get("/api/games/change_code")
    def change_code():
        tournament = request.args.get("tournament", type=str)
        game_id = int(request.args["id"])
        return jsonify({"code": comps[tournament].get_game(game_id).update_count})

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
        comps[tournament].get_game(game_id).teams[not first_team].sub_player(
            first_player
        )
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
        game = comps[tournament].get_game(game_id)
        if "official" in request.json:
            game.set_primary_official(next(i for i in comps[tournament].officials if i.nice_name() == request.json["official"]))
        game.start(
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

    @app.post("/api/games/update/swapServe")
    def swap_serve():
        tournament = request.json["tournament"]
        logger.info(f"Request for swap: {request.json}")
        game_id = request.json["id"]
        comps[tournament].get_game(game_id).swap_serve()
        comps[tournament].save()
        return "", 204

    @app.post("/api/games/update/swapServeTeam")
    def swap_serve_team():
        tournament = request.json["tournament"]
        logger.info(f"Request for swap: {request.json}")
        game_id = request.json["id"]
        comps[tournament].get_game(game_id).swap_serve_team()
        comps[tournament].save()
        return "", 204

    @app.post("/api/games/update/swapPlayerSides")
    def swap_player_sides():
        first_team = request.json.get("firstTeam", None)
        tournament = request.json["tournament"]
        logger.info(f"Request for swap: {request.json}")
        game_id = request.json["id"]
        comps[tournament].get_game(game_id).teams[not first_team].swap_players()
        comps[tournament].save()
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
            comps[tournament].get_game(game_id).teams[not first_team].red_card(
                first_player
            )

        comps[tournament].get_game(game_id).print_gamestate()
        comps[tournament].save()
        return "", 204
