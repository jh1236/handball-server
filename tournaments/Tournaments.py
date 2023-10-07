import os

from structure.Tournament import Tournament


def load_tournaments(root) -> list[Tournament]:
    ret: list[Tournament] = []
    for filename in os.listdir("./resources/tournaments"):
        f = os.path.join("./resources/tournaments", filename)
        if os.path.isfile(f):
            Tournament(f)

    return ret
