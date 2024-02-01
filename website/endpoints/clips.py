import os
import time

from flask import request, redirect

clip_id = 0
clip = {}
headers = [
    "id",
    "time",
    "certain",
    "teamOutcome",
    "personalOutcome",
    "starring",
    "quality",
    "tags",
]


def add_clip_endpoints(app, comps):
    global clip_id

    with open("./clips/details.csv") as fp:
        lines = fp.readlines()

    for i in lines:
        check_id = i.split(",")[0]
        if not check_id.isdigit():
            continue
        clip[int(check_id)] = {i: j for i, j in zip(headers, i.split(","))}

    folder = os.fsencode("./clips/")
    for i in os.listdir(folder):
        filename = os.fsdecode(i)
        if filename.endswith(".mp4"):  # whatever file types you're using...
            check_id = int(filename.split("_")[1].split(".")[0])
            if check_id not in clip:
                clip[check_id] = None

    @app.post("/api/clip/upload")
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
    def rate_file():
        print(request.json)
        key = request.json["key"]
        from start import admin_password

        if key != admin_password:
            return "<h1>invalid!!!</h1>", 403
        id = request.json["id"]

        clip[id] = {
            "id": id,
            "time": time.time(),
            "certain": request.json["certain"],
            "teamOutcome": request.json["teamOutcome"],
            "personalOutcome": request.json["personalOutcome"],
            "starring": request.json["starring"],
            "quality": request.json["quality"],
            "tags": request.json["tags"],
        }
        lines = [
            f"{','.join([str(j) for j in v.values()])}".strip('\n') for k, v in clip.items() if v
        ]
        with open("./clips/details.csv", "w") as fp:
            fp.write("\n".join(lines))
        return redirect(f"/video/unrated")

    @app.post("/api/clip/bookmark")
    def bookmark():
        print(request.json)
        with open("./clips/bookmark.txt", "a+") as fp:
            fp.write(f"{request.json['id']}: {request.json['reason']}")
