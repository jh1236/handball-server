import flask

from structure.Tournament import load_all_tournaments
from website.website import init_api

app = flask.Flask(__name__)
app.config["DEBUG"] = True
comps = load_all_tournaments()


init_api(app, comps)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
    # 5000: arbitrary port but one with higher value, lower ones might be reserved
