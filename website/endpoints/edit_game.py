import time

from flask import request, jsonify

from structure import manage_game
from utils.logging_handler import logger


def add_game_endpoints(app, comps):
    @app.get("/api/games/change_code")
    def change_code():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
            }
        """
        game_id = int(request.args["id"])
        return jsonify({"code": manage_game.change_code(game_id)})

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
        logger.info(f"Request for start: {request.json}")
        game_id = int(request.json["id"])
        swap_serve = request.json["swapService"]
        team_one = request.json.get("teamOne", None)
        team_two = request.json.get("teamTwo", None)
        first_is_iga = request.json["teamOneIGA"]
        umpire = request.json.get("official", None)
        scorer = request.json.get("scorer", None)
        manage_game.start_game(game_id, swap_serve, team_one, team_two,
                               first_is_iga,
                               umpire, scorer)
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
        game_id = int(request.json["id"])
        first_team = request.json["firstTeam"]
        left_player = request.json["leftPlayer"]
        manage_game.score_point(game_id, first_team, left_player)
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
        manage_game.ace(game_id)
        return "", 204

    @app.post("/api/games/update/substitute")
    def substitute():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                firstTeam: <bool> = if the team listed first is substituting
                leftPlayer: <bool> = if the player listed as left is leaving the court
            }
        """
        logger.info(f"Request for substitute: {request.json}")
        game_id = request.json["id"]
        first_team = request.json["firstTeam"]
        first_player = request.json["leftPlayer"]
        manage_game.substitute(game_id, first_team, first_player)
        return "", 204

    @app.post("/api/games/update/pardon")
    def pardon():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                firstTeam: <bool> = if the team listed first is being pardoned
                leftPlayer: <bool> = if the player listed as left is being pardoned
            }
        """
        logger.info(f"Request for substitute: {request.json}")
        game_id = request.json["id"]
        first_team = request.json["firstTeam"]
        first_player = request.json["leftPlayer"]
        manage_game.pardon(game_id, first_team, first_player)
        return "", 204

    @app.post("/api/games/update/end")
    def end():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                bestPlayer: <str> = the name of the best on ground
                notes: <str> (OPTIONAL) = any notes the umpire wishes to leave
                protestTeamOne: str = null if no protest, the reason if a protest is present
                protestTeamTwo: str = null if no protest, the reason if a protest is present
            }
        """
        logger.info(f"Request for end: {request.json}")
        game_id = request.json["id"]
        best = request.json.get("bestPlayer", None)
        manage_game.end_game(game_id, best, request.json.get("notes", None), request.json["protestTeamOne"],
                             request.json["protestTeamTwo"])
        return "", 204

    @app.post("/api/games/update/timeout")
    def timeout():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                firstTeam: <bool> = if the team listed first called the timeout
            }
        """
        logger.info(f"Request for timeout: {request.json}")
        first_team = request.json["firstTeam"]
        game_id = request.json["id"]
        manage_game.time_out(game_id, first_team)
        return "", 204

    @app.post("/api/games/update/forfeit")
    def forfeit():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                firstTeam: <bool> = if the team listed first forfeited
            }
        """
        logger.info(f"Request for forfeit: {request.json}")
        first_team = request.json["firstTeam"]
        game_id = request.json["id"]
        manage_game.forfeit(game_id, first_team)
        return "", 204

    @app.post("/api/games/update/end_timeout")
    def end_timeout():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
            }
        """
        logger.info(f"Request for end_timeout: {request.json}")
        game_id = request.json["id"]
        manage_game.end_timeout(game_id)
        return "", 204

    @app.post("/api/games/update/serve_clock")
    def serve_timer():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                start: <bool> = if the serve timer is starting or ending
            }
        """
        logger.info(f"Request for serve_clock: {request.json}")
        game_id = request.json["id"]
        manage_game.serve_timer(game_id, request.json['start'])
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
        manage_game.fault(game_id)
        return "", 204

    @app.post("/api/games/update/undo")
    def undo():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
            }
        """
        logger.info(f"Request for undo: {request.json}")
        game_id = request.json["id"]
        manage_game.undo(game_id)
        return "", 204

    @app.post("/api/games/update/delete")
    def delete():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
            }
        """
        logger.info(f"Request for delete: {request.json}")
        game_id = request.json["id"]
        manage_game.delete(game_id)
        return "", 204

    @app.post("/api/games/update/card")
    def card():
        """
        SCHEMA:
            {
                id: <int> = id of the current game
                firstTeam: <bool> = if the team listed first received the card
                leftPlayer: <bool> = if the player listed as left received the card
                color: <str> = the type of card ("Red", "Yellow", "Green", "Warning")
                duration: <int> = the amount of rounds the card carries
                reason: <str> = the reason for the card
            }
        """
        logger.info(f"Request for card: {request.json}")
        color = request.json["color"]
        first_team = request.json["firstTeam"]
        left_player = request.json["leftPlayer"]
        game_id = request.json["id"]
        duration = request.json["duration"]
        reason = request.json["reason"]
        manage_game.card(game_id, first_team, left_player, color, duration, reason)
        return "", 204
