import re
from itertools import zip_longest
from typing import TypeVar, Iterator
from urllib.request import urlopen, Request

from bs4 import BeautifulSoup

from database.models import Games

T = TypeVar("T")


def chunks_sized(lst: list[T], n: int) -> list[list[T]]:
    """Yield successive n-sized chunks from lst."""
    lizt = []
    for i in range(0, len(lst), n):
        lizt.append(lst[i: i + n])
    return lizt


def n_chunks(l: list[T], n: int, s=None) -> Iterator[list[T]]:
    """Yield n number of striped chunks from l."""
    l = l.copy()
    while s and len(l) % n != 0:
        l.append(s)
    for i in range(0, n):
        yield l[i::n]


def fixture_sorter(games: list[Games]) -> list[Games]:
    """INPUT: any object where id is list index 0 and court is list index 1 and isBye is list index 2"""

    court_one = [i for i in games if i.court == 0 and not i.is_bye]
    court_two = [i for i in games if i.court == 1 and not i.is_bye]
    byes = [i for i in games if i.is_bye]
    if not court_two:
        return court_one + byes
    this_round = []
    for g1, g2 in zip_longest(court_one, court_two):
        this_round.append(g1)
        this_round.append(g2)
    this_round = [i for i in this_round if i]
    return this_round + byes


def google_image(word):
    url = "https://www.google.com/search?tbm=isch&q=" + re.sub("[^a-zA-Z0-9]", "", word.replace(" ", "_"))
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
    req = Request(url, headers=headers)
    page = urlopen(req)
    bs = BeautifulSoup(page, 'html.parser')
    images = bs.find_all('img', {'src': re.compile('.*gstatic.com.*')})
    return images[0]['src']
