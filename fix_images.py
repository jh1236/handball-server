import threading
import time

from utils.databaseManager import DatabaseManager
from utils.util import google_image

active = 0
images = {}

last_time = 0

def load_image(id_in, name):
    global active
    images[id_in] = google_image(name)
    active -= 1


def load_images():
    global active, last_time
    with DatabaseManager() as c:
        teams = c.execute("""Select id, name FROM teams WHERE image_url is null""").fetchall()
        for id, url in teams:
            active += 1
            threading.Thread(target=lambda: load_image(id, url)).start()
        while active:
            if last_time < time.time():
                print(f"waiting on {active} threads")
                last_time = time.time() + .5
        for id, url in images.items():
            c.execute("""UPDATE teams SET image_uRL = ? WHERE id = ?""", (url, id))


if __name__ == "__main__":
    load_images()
