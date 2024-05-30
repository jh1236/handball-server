import time

from flask import request, jsonify

from structure import manageGame
from utils.logging_handler import logger


def add_game_endpoints(app, comps):
    @app.get("/api/games/change_code")
    def change_code():
        tournament = request.args.get("tournament", type=str)
        game_id = int(request.args["id"])
        return jsonify({"code": comps[tournament].get_game(game_id).update_count})

    @app.post("/api/games/update/start")
    def start():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                swapService: <bool> = if the team listed first is serving
                teamOneIGA: <bool> = if the team listed first is on the IGA side of the court
                teamOne: <list[str]> = the names team listed first in order [left, right, substitute]
                teamTwo: <list[str]> = the names team listed second in order [left, right, substitute]
                official: <str> (OPTIONAL) = the official who is actually umpiring the game
                scorer: <str> (OPTIONAL) = the scorer who is actually scoring the game
            }
        """
        game_id = int(request.args["id"])
        manageGame.start_game(game_id, request.json["swapService"], request.json["teamOne"], request.json["teamTwo"], request.json["teamOneIGA"],
                              request.json.get("official", None), request.json.get("scorer", None))
        return "", 204

    @app.post("/api/games/update/score")
    def score():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                firstTeam: <bool> = if the team listed first scored
                leftPlayer: <bool> = if the player listed as left scored
            }
        """
        logger.info(f"Request for score: {request.json}")
        game_id = int(request.args["id"])
        manageGame.score_point(game_id, request.json["firstTeam"], request.json["leftPlayer"])
        return "", 204

    @app.post("/api/games/update/ace")
    def ace():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
            }
        """
        logger.info(f"Request for ace: {request.json}")
        game_id = request.json["id"]
        manageGame.ace(game_id)
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
        """
        SCHEMA:
            {
                id: <int> = id of the current game
            }
        """
        logger.info(f"Request for fault: {request.json}")
        game_id = request.json["id"]
        manageGame.fault(game_id)
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
            comps[tournament].get_game(game_id, ).teams[
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
