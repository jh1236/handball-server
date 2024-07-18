import flask

from database import db
from website.website import init_api

app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config['SECRET_KEY'] = 'secret!'

db.init_app(app)
init_api(app)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
