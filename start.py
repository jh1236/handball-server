import flask
from flask_socketio import SocketIO

from structure.Tournament import load_all_tournaments
from unrelated.Fuck import add_unrelated_endpoints
from website.website import init_api

app = flask.Flask(__name__)
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
comps = load_all_tournaments()


init_api(app, comps)
add_unrelated_endpoints(app, socketio)

def fun():
    pass

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=80, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
