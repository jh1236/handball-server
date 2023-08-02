import math

from structure.Fixture import Fixture
from tournaments.Tournament import Tournament
from util import chunks_sized


class SingleElim(Tournament):
    def __init__(self, teams):
        super().__init__(teams)

    def generate_fixtures(self) -> [Fixture]:
        out: list[Fixture] = []
        games = self.teams.copy()
        n = int(math.log2(len(games)) != math.floor(math.log2(len(games))))
        i = len(games)
        while math.log2(len(games)) != math.floor(math.log2(len(games))):
            i -= 1
            f = Fixture(games[i], games[i - 1], n, self)
            games[i] = f.winner
            del games[i - 1]
            print(games)
            out.append(f)
        print(f"level {n}: {out}")
        games: list[Fixture] = [Fixture(i[0], i[1], n, self) for i in chunks_sized(games, 2) if i]
        while len(games) > 1:
            out += games
            n += 1
            print(f"level {n}: {games}")
            games = [Fixture(i.winner, j.winner, n, self) for i, j in chunks_sized(games, 2) if i or j]
        out += games
        return out
