from utils.sidebar_wrapper import render_template_sidebar


def add_universal_tournament(app):
    @app.get("/signup/")
    def sign_up_page():
        tournament = "Seventh S.U.S.S Championship"
        countries = [
            "Kiribati",
            "Sahrawi Arab Democratic Republic",
            "Saint Vincent and the Grenadines",
            "Kazakhstan",
            "Azerbaijan",
            "Trinidad & Tobago",
            "Armenia",
            "Panama",
            "Saint Kits",
            "Guatemala",
            "Mozambique",
            "Andorra",
            "San Marino",
            "Djibouti",
            "Mauritania",
            "Mauritius",
            "Burkina Faso",
            "Equatorial Guinea",
            "Lesotho",
            "Senegal",
            "Moldova",
            "Bhutan",
            "Upstate New York",
            "Austria",
            "Suriname",
            "Lichenstein",
            "Val Verde",
            "Transcaucasian Socialist Federative Soviet Republic",
            "Vatican City",
            "International Waters"
        ]
        countries.sort()
        return (
            render_template_sidebar(
                "sign_up/olympic.html",
                countries=countries,
                tournament=tournament,
            ),
            200,
        )
