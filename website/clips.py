import time
from random import Random

from flask import render_template, send_from_directory, request, redirect, send_file

from structure.AllTournament import get_all_officials
from utils.permissions import admin_only, officials_only
from website.endpoints.clips import clip

umpire_stats = {}
answers = []


card_numbers = {
    "No Card": 0,
    "Green Card": 4,
    "Yellow Card": 8,
    "Extended Yellow Card (4-6 rounds)": 9,
    "Extended Yellow Card (7+ rounds)": 10,
    "Red Card": 16
}


def process_videos(videos, tags, name):
    videos = [i for i in videos if i["time"]]
    for tag in tags.split(","):
        if tag == "new":
            seen_videos = [j["id"] for j in answers if j["name"] == name]
            videos = [i for i in videos if str(i["id"]) not in seen_videos]
        elif tag == "old":
            seen_videos = [j["id"] for j in answers if j["name"] == name]
            videos = [i for i in videos if str(i["id"]) in seen_videos]
        elif tag == "wrong":
            wrong_videos = [
                j["id"] for j in answers if j["name"] == name and not j["correct"]
            ]
            videos = [i for i in videos if str(i["id"]) in wrong_videos]
        elif tag == "required":
            with open("./clips/required.txt") as fp:
                reqd = [i.strip() for i in fp.readlines()]
            videos = [i for i in videos if str(i["id"]) in reqd]
        elif tag.startswith("!"):
            videos = [i for i in videos if tag[1:] not in i["tags"].strip().split("|")]
        else:
            videos = [i for i in videos if tag in i["tags"].strip().split("|")]
    return videos


def add_video_player(app, comps):
    answers.clear()
    umpire_stats.clear()
    for i in get_all_officials():
        umpire_stats[i.nice_name()] = {
            "team_correct": 0,
            "personal_correct": 0,
            "total_correct": 0,
            "answered": 0,
            "bias": 0,
        }
    answers.clear()
    with open("./clips/attempts.csv", "r") as fp:
        for i in fp.readlines():
            splt = i.strip().split(",")
            # {id},{time.time()},{name},{answer_team},{answer_personal}
            add_to_answers(splt[2], int(splt[0]), splt[3], splt[4], float(splt[1]))

    @app.get("/upload/")
    @admin_only
    def upload():
        return render_template("clips/upload.html")

    @app.get("/video/<id>/raw")
    def raw_video(id):
        return send_from_directory("clips/videos", f"clip_{id}.mp4")

    @app.get("/video/<id>/admin")
    @admin_only
    def rate_video(id):
        key = request.args.get("key", None)

        official = next(i for i in get_all_officials() if i.key == key)
        rated_by_me = [i for i in clip if i["rater"] == official.nice_name()]
        not_by_me = [
            i for i in clip if not str(i["rater"]) == official.nice_name() and i["time"]
        ]
        conflict = False
        tags = []
        team = "Team Outcome"
        personal = "Personal Outcome"
        starring = ""
        certain = False
        for i in rated_by_me:
            if str(i["id"]) == str(id):
                tags += [k for k in i["tags"].split("|") if k not in tags]
                starring = i["starring"].replace("|", ",")
                team = i["teamOutcome"].strip()
                personal = i["personalOutcome"].strip()
                certain = str(i["certain"]).replace(" ", "").replace("\n", "") == "True"
                print(certain)
            for j in not_by_me:
                if str(j["id"]) == str(id):
                    tags += [k for k in j["tags"].split("|") if k not in tags]
                    if not starring:
                        starring = j["starring"].replace("|", ",")
                if i["id"] != j["id"]:
                    continue
                if (
                    i["personalOutcome"] == j["personalOutcome"]
                    and i["teamOutcome"] == j["teamOutcome"]
                ):
                    continue
                conflict = True
                break
        tags = ",\n".join(tags)
        bookmarked = False
        with open("./clips/bookmark.txt", "r") as fp2:
            for i in fp2.readlines():
                if int(i.split(":")[0]) == int(id):
                    bookmarked = True
                    break
        with open("./clips/required.txt") as fp:
            reqd = [i.strip() for i in fp.readlines()]
        return render_template(
            "clips/viewer_admin.html",
            id=id,
            key=key,
            bookmarked=bookmarked,
            conflict=conflict,
            tags=tags,
            starring=starring,
            team=team,
            personal=personal,
            certain=certain,
            required=str(id) in reqd,
            url_tags=url_tags,
        )

    @app.get("/video/conflict")
    @admin_only
    def conflict_video():
        key = request.args.get("key", None)
        official = next(i for i in get_all_officials() if i.key == key)
        rated_by_me = [i for i in clip if i["rater"] == official.nice_name()]
        not_by_me = [
            i
            for i in clip
            if not str(i["rater"]) == official.nice_name()
            and i["id"] in [j["id"] for j in rated_by_me]
        ]
        conflict = False
        tags = ""
        for i in rated_by_me:
            for j in not_by_me:
                if i["id"] != j["id"]:
                    continue
                if (
                    i["personalOutcome"] == j["personalOutcome"]
                    and i["teamOutcome"] == j["teamOutcome"]
                ):
                    continue
                conflict = (i, j)
                tags = ",\n".join(
                    [
                        k
                        for k in j["tags"].split("|")
                        if k not in i["tags"].split("|") and k
                    ]
                    + i["tags"].split("|")
                )
                break
        lines = [
            f"{','.join([str(j) for j in v.values()])}".strip("\n")
            for v in clip
            if v["time"]
        ]
        lines.sort(key=lambda a: int(a.split(",")[0]))
        with open("./clips/details.csv", "w") as fp:
            fp.write("\n".join(lines))
        if conflict:
            return render_template(
                "clips/viewer_conflict.html",
                id=conflict[0]["id"],
                key=key,
                me=conflict[0],
                other=conflict[1],
                tags=tags,
            )
        else:
            return redirect(f"/video/unrated?key={key}")

    @app.get("/video/<id>/answer/admin")
    def every_answer(id):
        key = request.values["key"]
        if key not in [i.key for i in get_all_officials()]:
            return (
                render_template(
                    "tournament_specific/game_editor/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        details = sorted(
            [i for i in clip if str(i["id"]) == str(id) if i["time"]],
            key=lambda a: a["time"],
        )[
            -1
        ]  # TODO: make me take all answers into account
        team = details["teamOutcome"]
        personal = details["personalOutcome"]
        ans = sorted([i for i in answers if str(i["id"]) == id], key=lambda a: ((a["name"], -float(a["time"]))))
        print(ans)
        return render_template(
            "clips/viewer_all_answers.html",
            answers=ans,
            key=key,
            id=id,
            true_team=team,
            true_personal=personal,
        )

    @app.get("/video/unrated")
    @admin_only
    def next_unrated_video():
        key = request.args.get("key", None)
        official = next(i for i in get_all_officials() if i.key == key)
        rated_by_me = [i for i in clip if i["rater"] == official.nice_name()]
        not_by_me = [
            i for i in clip if str(i["id"]) not in [str(j["id"]) for j in rated_by_me]
        ]
        id = request.args.get("id", None, type=int)
        if not not_by_me:
            if id:
                return redirect(f"/video/{id+1}/admin?key={key}")
            return redirect(f"/video?key={key}")
        id = Random().choice(not_by_me)["id"]
        return redirect(f"/video/{id}/admin?key={key}")

    @app.get("/video/next/admin")
    def random_admin_video():
        key = request.args.get("key", None)
        tags = request.args.get("tags", "")
        if key not in [i.key for i in get_all_officials() if i.admin]:
            return (
                render_template(
                    "tournament_specific/admin/no_access.html",
                    error="The password you entered is not correct",
                ),
                403,
            )
        official = next(i for i in get_all_officials() if i.key == key)

        videos = [i for i in clip if i["rater"] == official.nice_name()]
        videos += [i for i in clip if str(i["id"]) not in [j["id"] for j in videos]]
        if tags:
            videos = process_videos(videos, tags, official.nice_name())
        rand = Random()
        videos.sort(key=lambda a: float(a["time"] or -rand.randint(0, 100)))
        if not videos:
            return redirect(f"/video?key={key}")
        id = videos[0]["id"]
        if tags:
            return redirect(f"/video/{id}/admin?key={key}&tags={tags}")
        else:
            return redirect(f"/video/{id}/admin?key={key}")

    @app.get("/video/answers.csv")
    @admin_only
    def get_answers():
        return send_file("./clips/attempts.csv")

    @app.get("/video/<id>")
    @officials_only
    def test_video(id):
        tags = request.args.get("tags", "")
        key = request.args.get("key", None)
        name = next(
            (i.nice_name() for i in get_all_officials() if i.key == key), "admin"
        )
        stats = umpire_stats[name]
        details = [i for i in clip if str(i["id"]) == str(id)]
        starring = details[0]["starring"].replace("|", ", ")
        if tags:
            return render_template(
                "clips/viewer.html",
                id=id,
                key=key,
                starring=starring,
                stats=stats,
                tags=tags,
            )
        else:
            return render_template(
                "clips/viewer.html", id=id, key=key, starring=starring, stats=stats
            )

    @app.post("/video/<id>/answer")
    @officials_only
    def answer_video(id):
          = request.values["key"]
        tags = request.values.get("tags", "")
        details = sorted(
            [i for i in clip if str(i["id"]) == str(id) if i["time"]],
            key=lambda a: a["time"],
        )[
            -1
        ]  # TODO: make me take all answers into account
        starring = details["starring"].replace("|", ", ")
        answer_team = request.values["teamOutcome"]
        answer_personal = request.values["personalOutcome"]
        team = details["teamOutcome"]
        personal = details["personalOutcome"]
        team_correct = team == answer_team or team == "Unclear"
        personal_correct = personal == answer_personal
        name = next(
            (i.nice_name() for i in get_all_officials() if i.key == key), "admin"
        )
        with open("./clips/attempts.csv", "a+") as fp:
            fp.write(f"{id},{time.time()},{name},{answer_team},{answer_personal}\n")
        add_to_answers(name, id, answer_team, answer_personal, time.time())
        return render_template(
            "clips/answer.html",
            id=id,
            key=key,
            tags=tags,
            starring=starring,
            team=answer_team,
            personal=answer_personal,
            team_correct=team_correct,
            personal_correct=personal_correct,
        )

    @app.get("/video/random")
    @officials_only
    def random_video():
        key = request.args.get("key", None)
        tags = request.args.get("tags", "")
        videos = [i for i in clip if i["time"] and int(i["quality"])]
        official = next(i for i in get_all_officials() if i.key == key)
        rated_by_me = [i for i in clip if i["rater"] == official.nice_name()]
        not_by_me = [
            i
            for i in clip
            if not str(i["rater"]) == official.nice_name()
            and i["id"] in [j["id"] for j in rated_by_me]
        ]
        conflict = []
        for i in rated_by_me:
            for j in not_by_me:
                if i["id"] != j["id"]:
                    continue
                if (
                    i["personalOutcome"] == j["personalOutcome"]
                    and i["teamOutcome"] == j["teamOutcome"]
                ):
                    continue
                conflict.append(i["id"])
        if tags:
            videos = process_videos(videos, tags, official.nice_name())
        videos = [i for i in videos if i["id"] not in conflict]
        if not videos:
            return redirect(f"/video?key={key}")
        id = Random().choice(videos)["id"]
        if tags:
            return redirect(f"/video/{id}?key={key}&tags={tags}")
        else:
            return redirect(f"/video/{id}?key={key}")

    @app.get("/video/")
    @officials_only
    def video_homepage():
        key = request.args.get("key", None)
        official = next(i for i in get_all_officials() if i.key == key)
        wrong_videos = [
            j for j in answers if j["name"] == official.nice_name() and not j["correct"]
        ]
        wrong_categories = {}
        for i in wrong_videos:
            for j in i["tags"].split("|"):
                if not j.strip():
                    continue
                wrong_categories[j] = wrong_categories.get(j, 0) + 1
        wrong = sorted(
            wrong_categories.keys(), key=lambda a: wrong_categories[a], reverse=True
        )
        if len(wrong) > 4:
            wrong = wrong[:4]
        with open("./clips/required.txt") as fp:
            reqd = [i.strip() for i in fp.readlines()]
        seen_videos = [
            str(j["id"]) for j in answers if j["name"] == official.nice_name()
        ]
        reqd = [i for i in reqd if i not in seen_videos]
        if len(reqd) > 4:
            reqd = reqd[:4]
        return render_template("clips/video_home.html", key=key, wrong=wrong, reqd=reqd)


def add_to_answers(name, id, team, personal, time):
    details = sorted(
        [i for i in clip if str(i["id"]) == str(id) if i["time"]],
        key=lambda a: a["time"],
    )[-1]
    true_team = details["teamOutcome"]
    true_personal = details["personalOutcome"]
    team_correct = team == true_team or true_team == "Unclear"
    personal_correct = personal == true_personal
    umpire_stats[name] = {
        "team_correct": umpire_stats[name]["team_correct"] + team_correct,
        "personal_correct": umpire_stats[name]["personal_correct"] + personal_correct,
        "total_correct": umpire_stats[name]["total_correct"]
        + (team_correct and personal_correct),
        "answered": umpire_stats[name]["answered"] + 1,
        "bias": umpire_stats[name]["bias"]
        + (
            card_numbers[personal] - card_numbers[true_personal]
            if details["certain"]
            else 0
        ),
    }
    answers.append(
        {
            "id": str(id),
            "time": time,
            "name": name,
            "correct": team_correct and personal_correct,
            "providedTeam": team,
            "providedPersonal": personal,
            "trueTeam": true_team,
            "truePersonal": true_personal,
            "tags": details["tags"],
        }
    )
