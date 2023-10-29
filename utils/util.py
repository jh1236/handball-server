import math
from typing import TypeVar, Any

T = TypeVar("T")


def chunks_sized(lst: list[T], n: int) -> list[list[T]]:
    """Yield successive n-sized chunks from lst."""
    lizt = []
    for i in range(0, len(lst), n):
        lizt.append(lst[i : i + n])
    return lizt


def probability(rating1, rating2):
    return 1.0 * 1.0 / (1 + 1.0 * math.pow(10, 1.0 * (rating1 - rating2) / 400))


def n_chunks(l: list[T], n: int, s=None) -> list[list[T]]:
    """Yield n number of striped chunks from l."""
    l = l.copy()
    while s and len(l) % n != 0:
        l.append(s)
    for i in range(0, n):
        yield l[i::n]


def calc_elo(team_one, team_two, first_won):
    K = 60
    pa = probability(team_two.elo, team_one.elo)
    ra = team_one.elo + K * (first_won - pa)

    return ra - team_one.elo


def fixture_sorter(fixtures: list[list[Any]]) -> list[list[Any]]:
    output = []
    for r in fixtures:
        r = r.copy()
        r.sort(key=lambda a: a.id)
        court = False
        new_round = []
        while r:
            new_round.append(
                r.pop(next((i for i, v in enumerate(r) if v.court == court), 0))
            )
            court = not court
        output.append(new_round)
    return output
