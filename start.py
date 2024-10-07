import flask

from database import db
from website.website import init_api
# from waitress import serve
from flask_minify import Minify
from utils.logging_handler import logger

logger.setLevel("INFO")

app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config['SECRET_KEY'] = 'secret!'

Minify(app=app, html=True, js=True, cssless=True)

db.init_app(app)
init_api(app)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    print("Starting server")
    # serve(app, host='127.0.0.1', port=8080)
    app.run(host="0.0.0.0", port=80, debug=False, use_reloader=False, ssl_context=None)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved