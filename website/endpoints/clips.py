import os
import time

from flask import request, redirect

from structure.AllTournament import get_all_officials
from utils.permissions import admin_only, fetch_user

clip_id = 0
clip = []
headers = [
    "id",
    "time",
    "rater",
    "certain",
    "teamOutcome",
    "personalOutcome",
    "starring",
    "quality",
    "tags",
]


def add_clip_endpoints(app, comps):
    global clip_id
    global clip

    with open("./clips/details.csv") as fp:
        lines = fp.readlines()
    clip.clear()
    for i in lines:
        check_id = i.split(",")[0]
        if not check_id.isdigit():
            continue
        clip.append({i: j for i, j in zip(headers, i.split(","))})
    folder = os.fsencode("./clips/videos/")
    for i in os.listdir(folder):
        filename = os.fsdecode(i)
        if filename.endswith(".mp4"):
            check_id = int(filename.split("_")[1].split(".")[0])
            if check_id not in [k["id"] for k in clip]:
                d = {i: None for i in headers}
                d["id"] = check_id
                clip.append(d)

    @app.post("/api/clip/upload")
    @admin_only
    def upload_file():
        global clip_id
        if request.method == "POST":
            # try:
            files = request.files.getlist("file")
            old_id = clip_id
            for file in files:
                file.save(f"./clips/clip_{clip_id}.mp4")
                clip_id += 1
            with open("./clips/id.txt", "w") as fp:
                fp.write(str(clip_id))
            return redirect(f"/video/{old_id}")
        # except Exception:
        #     pass
        return "<h1>An error Occured Uploading!</h1>", 500

    @app.post("/api/clip/rate")
    @admin_only
    def rate_file():
        key = fetch_user()
        name = next(
            i.nice_name() for i in get_all_officials() if i.key == key
        )
        starring = None
        quality = request.json.get("quality", None)
        id = request.json["id"]
        idx = None
        for n, i in enumerate(clip):
            if str(i["id"]) == str(id) and i["rater"] == name:
                if starring is None:
                    starring = i["starring"]
                if quality is None:
                    quality = i["quality"]
                idx = n
                break
        if idx is not None:
            del clip[idx]

        if starring is None:
            starring = request.json["starring"]
        if quality is None:
            quality = request.json["starring"]
        clip.append(
            {
                "id": str(id),
                "time": time.time(),
                "rater": name,
                "certain": request.json["certain"],
                "teamOutcome": request.json["teamOutcome"].strip(" \n"),
                "personalOutcome": request.json["personalOutcome"].strip(" \n"),
                "starring": starring.strip(" \n"),
                "quality": quality,
                "tags": request.json["tags"].strip(" \n"),
            }
        )
        lines = [
            f"{','.join([str(j) for j in v.values()])}".strip("\n")
            for v in clip
            if v["time"]
        ]
        lines.sort(key=lambda a: int(a.split(",")[0]))
        print([i["id"] for i in clip if i["time"]])
        with open("./clips/details.csv", "w") as fp:
            fp.write("\n".join(lines))
        with open("./clips/required.txt", "r") as fp:
            reqd = fp.readlines()
        reqd = list(set(reqd))
        if request.json["required"]:
            if str(id) not in [i.strip() for i in reqd]:
                with open("./clips/required.txt", "a+") as fp:
                    fp.write(f"{id}\n")
        else:
            with open("./clips/required.txt", "w") as fp:
                fp.writelines([i for i in reqd if i.strip() != str(id)])
        return redirect(f"/video/unrated")

    @app.post("/api/clip/bookmark")
    def bookmark():
        print(request.json)
        with open("./clips/bookmark.txt", "a+") as fp:
            fp.write(f"{request.json['id']}: {request.json['reason']}\n")

