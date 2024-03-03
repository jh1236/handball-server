from flask import render_template, Response

from structure.AllTournament import (
    get_all_players,
)
from structure.Tournament import Tournament
from utils.statistics import get_player_stats


def add_universal_tournament(app, comps: dict[str, Tournament]):

    @app.get("/signup/")
    def sign_up_page():
        tournament = "Fifth S.U.S.S Championship"
        return (
            render_template(
                "sign_up/new.html",
                tournament=tournament,
            ),
            200,
        )
