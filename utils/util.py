import math
from typing import TypeVar, Any

from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
import re

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


def calc_elo(elo, elo_other, first_won):
    K = 30
    pa = probability(elo_other, elo)
    ra = K * (first_won - pa)

    return ra


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



def google_image(word):
    # raise Exception("asd")
    url = "https://www.google.com/search?tbm=isch&q=" + re.sub("[^a-zA-Z0-9]","",word.replace(" ", "_"))
    headers = {'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
    req = Request(url, headers=headers)
    page = urlopen(req)
    bs = BeautifulSoup(page, 'html.parser')
    images = bs.find_all('img', {'src':re.compile('.*gstatic.com.*')})
    return images[0]['src']