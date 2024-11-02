from flask import request, Response

import utils.permissions
from database import db
from database.models import People


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

    @app.post("/api/image")
    def set_user_image():
        """
        SCHEMA:
        {
            user_id: <int> = id of the user attempting to log in
            image_location: <str> = The URL of the image to be used
        }
        """
        user_id = request.json.get("user_id")
        image_location = request.json.get("image_location")
        People.query.filter(People.user_id == user_id).image_url = image_location
        db.session.commit()
