import math

from structure.Fixture import Fixture
from tournaments.Tournament import Tournament
from util import chunks_sized


class SingleElim(Tournament):
    def __init__(self, teams):
        super().__init__(teams)

    def generate_round(self):
        out: list[Fixture] = []
        games = self.teams.copy()
        i = len(games)
        n = 0
        while math.log2(len(games)) != math.floor(math.log2(len(games))):
            n = 1
            i -= 1
            f = Fixture(games[i], games[i - 1], 0, self)
            games[i] = f.winner
            del games[i - 1]
            print(games)
            out.append(f)
        yield out
        games: list[Fixture] = [Fixture(i[0], i[1], n, self) for i in chunks_sized(games, 2) if i]
        while len(games) > 1:
            print("Called)")
            yield games
            n += 1
            print(f"level {n}: {games}")
            games = [Fixture(i.winner, j.winner, n, self) for i, j in chunks_sized(games, 2) if i or j]