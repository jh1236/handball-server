from utils.sidebar_wrapper import render_template_sidebar


def add_universal_tournament(app):

    @app.get("/signup/")
    def sign_up_page():
        tournament = "Sixth S.U.S.S Championship"
        return (
            render_template_sidebar(
                "sign_up/new.html",
                tournament=tournament,
            ),
            200,
        )

