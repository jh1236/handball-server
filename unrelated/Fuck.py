import time
from random import Random

from flask import render_template, request
from flask_socketio import emit

from utils.permissions import officials_only

COLORS = ["red", "purple", "yellow", "orange", "green", "blue"]
SWEARS = ["fuck", "shit", "pussy", "cock", "asshole"]
COLOR_TO_HEX = {
    "red": ["B71C1B","F44336","E57373"],
    "purple": ["71118e", "8E24AA", "BA67C8"],
    "blue": ["1A237E", "3949AB", "7986CB"],
    "green": ["33691D", "7CB242", "AED581"],
    "yellow": ["d6af11", "fade6e", "fae89d"],
    "orange": ["d97109", "faa652", "facb9d"],
    "black": ["000000", "000000", "000000"]
}
palette = 0
players = {}
rand = Random()
stack_size = 0


def get_colors():
    fg_colors = COLORS + ["black"]
    fg_color = bg_color = rand.choice(COLORS)
    while fg_color == bg_color:
        fg_color = rand.choice(fg_colors)
    text = rand.choice(COLORS + SWEARS).upper()
    print(bg_color, fg_color, text)
    # fg_color = "#" + rand.choice(COLOR_TO_HEX[fg_color])
    # bg_color = "#" + rand.choice(COLOR_TO_HEX[bg_color])
    fg_color = "#" + COLOR_TO_HEX[fg_color][palette]
    bg_color = "#" + COLOR_TO_HEX[bg_color][palette]
    return bg_color, fg_color, text


color = get_colors()


def add_unrelated_endpoints(app, socketio):
    @app.get("/misc/fuck")
    @officials_only
    def fuck():
        return render_template("/unrelated/fuck.html")

    @socketio.on("connect")
    def handle_my_custom_event():
        players[request.cookies.get("userName")] = 15
        send_gamestate()

    @socketio.on("disconnect")
    def leave():
        del players[request.cookies.get("userName")]
        send_gamestate()

    @socketio.on("next")
    def next_color(json):
        global color, stack_size
        color = get_colors()
        if json["correct"]:
            players[request.cookies.get("userName")] -= 1
            stack_size += 1
            if not players[request.cookies.get("userName")]:
                emit("game won", {"winner": request.cookies.get("userName")}, broadcast=True)
                for i in players:
                    players[i] = 15
                stack_size = 0
                send_gamestate()
            else:
                send_gamestate()
        else:
            players[request.cookies.get("userName")] += stack_size - 1
            stack_size = 1
            send_gamestate()

    @socketio.on("disco")
    def disco():
        global color
        while True:
            color = get_colors()
            send_gamestate()

    def send_gamestate():
        emit(
            "gamestate",
            {
                "fg_color": color[1],
                "bg_color": color[0],
                "text": color[2],
                "players": players,
                "time": round(time.time() * 1000)
            },
            broadcast=True,
        )
