from flask import request, Response
import utils.permissions
from database.models import People
from utils.sidebar_wrapper import render_template_sidebar


def add_user_endpoints(app):
    @app.post("/api/login")
    def login():
        """
        SCHEMA:
            {
                user_id: <int> = id of the user attempting to log in
                password: <str> = password of the user attempting to log in
            }
        """
        user_id = request.json.get("user_id")
        password = request.json.get("password")
        if utils.permissions.check_password(user_id, password):
            token = utils.permissions.get_token(user_id, password)
            # set cookie to token
            response = Response("Logged in", 200)
            response.set_cookie('token', token)
            response.set_cookie('userID', user_id)
            return response
        return "Wrong Password", 403

    @app.post("/api/logout")
    def api_logout():
        """
        SCHEMA:
        {

        }
        """
        utils.permissions.logout()
        return "Logged out", 200
