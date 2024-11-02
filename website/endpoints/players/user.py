import os

from flask import request, Response, send_file

from utils import permissions
from database import db
from database.models import People


def add_user_endpoints(app):
    @app.post("/api/login")
    def login():
        """
        SCHEMA:
        {
            userId: <int> = id of the user attempting to log in
            password: <str> = password of the user attempting to log in
        }
        """
        user_id = request.json.get("userId")
        password = request.json.get("password")
        if permissions.check_password(user_id, password):
            token = permissions.get_token(user_id, password)
            # set cookie to token
            response = Response({"token": token}, 200)
            response.set_cookie('token', token)
            response.set_cookie('userID', user_id)
            return response
        return "Wrong Password", 403

    @app.post("/api/image")
    @permissions.officials_only
    def set_user_image():
        """
        SCHEMA:
        {
            imageLocation: <str> = The URL of the image to be used
        }
        """
        user_id = permissions.fetch_user().id
        image_location = request.json.get("imageLocation")
        People.query.filter(People.user_id == user_id).image_url = image_location
        db.session.commit()
        return "", 204

    @app.get("/api/users/image")
    def user_image():
        team = request.args.get("name", type=str)
        if os.path.isfile(f"./resources/images/users/{team}.png"):
            return send_file(
                f"./resources/images/users/{team}.png", mimetype="image/png"
            )
        else:
            return send_file(f"./resources/images/umpire.png", mimetype="image/png")
