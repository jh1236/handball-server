import time
from random import Random

from flask import render_template, send_from_directory, request, redirect

from start import admin_password
from structure.AllTournament import get_all_officials
from website.endpoints.clips import clip_id, clip


answers = {}

card_numbers = {
    "No Card": 0,
    "Green Card": 4,
    "Yellow Card": 8,
    "Extended Yellow Card (4-6 rounds)": 9,
    "Extended Yellow Card (7+ rounds)": 10,
    "Red Card": 16,
}


def add_video_player(app, comps):
    for i in get_all_officials():
        answers[i.nice_name()] = {
            "team_correct": 0,
            "personal_correct": 0,
            "total_correct": 0,
            "answered": 0,
            "bias": 0,
        }
    with open("./clips/attempts.csv", "r") as fp:
        for i in fp.readlines():
            splt = i.strip().split(",")
            # {id},{time.time()},{name},{answer_team},{answer_personal}
            add_to_answers(splt[2], int(splt[0]), splt[3], splt[4])

    @app.get("/upload/")
    def upload():
        return render_template("clips/upload.html")

    @app.get("/video/<id>/raw")
    def raw_video(id):
        return send_from_directory("clips/videos", f"clip_{id}.mp4")

    @app.get("/video/<id>/admin")
    def rate_video(id):
        key = request.args.get("key", None)
        if key != admin_password:
            return (
                render_template(
                    "tournament_specific/admin/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        bookmarked = False
        with open("./clips/bookmark.txt", "r") as fp:
            for i in fp.readlines():
                if int(i.split(":")[0]) == int(id):
                    bookmarked = True
                    break
        return render_template(
            "clips/viewer_admin.html", id=id, key=key, bookmarked=bookmarked
        )

    @app.get("/video/unrated")
    def next_unrated_video():
        key = request.args.get("key", None)
        if key != admin_password:
            return (
                render_template(
                    "tournament_specific/admin/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        id = next(i for i, k in clip.items() if not k)
        return redirect(f"/video/{id}/admin?key={key}")

    @app.get("/video/<id>")
    def test_video(id):
        key = request.args.get("key", None)
        if key not in [i.key for i in get_all_officials()] + [admin_password]:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        name = next(
            (i.nice_name() for i in get_all_officials() if i.key == key), "admin"
        )
        stats = answers[name]
        starring = clip[int(id)]["starring"].replace("|", ", ")
        return render_template(
            "clips/viewer.html", id=id, key=key, starring=starring, stats=stats
        )

    @app.post("/video/<id>/answer")
    def answer_video(id):
        key = request.values["key"]
        if key not in [i.key for i in get_all_officials()] + [admin_password]:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )

        starring = clip[int(id)]["starring"].replace("|", ", ")
        print(request.values)
        answer_team = request.values["teamOutcome"]
        answer_personal = request.values["personalOutcome"]
        team = clip[int(id)]["teamOutcome"]
        personal = clip[int(id)]["personalOutcome"]
        team_correct = team == answer_team
        personal_correct = personal == answer_personal
        name = next(
            (i.nice_name() for i in get_all_officials() if i.key == key), "admin"
        )
        with open("./clips/attempts.csv", "a+") as fp:
            fp.write(f"{id},{time.time()},{name},{answer_team},{answer_personal}\n")
        add_to_answers(name, id, answer_team, answer_personal)
        return render_template(
            "clips/answer.html",
            id=id,
            key=key,
            starring=starring,
            team=answer_team,
            personal=answer_personal,
            team_correct=team_correct,
            personal_correct=personal_correct,
        )

    @app.get("/video/random")
    def random_video():
        key = request.args.get("key", None)
        if key not in [i.key for i in get_all_officials()] + [admin_password]:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        id = Random().choice([i for i, k in clip.items() if k and int(k["quality"])])
        return redirect(f"/video/{id}?key={key}")


def add_to_answers(name, id, team, personal):
    true_team = clip[int(id)]["teamOutcome"]
    true_personal = clip[int(id)]["personalOutcome"]
    team_correct = team == true_team
    personal_correct = personal == true_personal
    answers[name] = {
        "team_correct": answers[name]["team_correct"] + team_correct,
        "personal_correct": answers[name]["personal_correct"] + personal_correct,
        "total_correct": answers[name]["total_correct"]
        + (team_correct and personal_correct),
        "answered": answers[name]["answered"] + 1,
        "bias": answers[name]["bias"]
        + (
            card_numbers[personal] - card_numbers[true_personal]
            if clip[int(id)]["certain"]
            else 0
        ),
    }
