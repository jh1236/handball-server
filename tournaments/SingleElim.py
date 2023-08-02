import math

from structure.Fixture import Fixture
from tournaments.Tournament import Tournament
from util import chunks_sized


class SingleElim(Tournament):
    def __init__(self, teams):
        self.teams_balanced: list = teams.copy()
        while math.log2(len(self.teams_balanced)) != math.floor(math.log2(len(self.teams_balanced))):
            self.teams_balanced += [None]
        super().__init__(teams)

    def generate_fixtures(self) -> [Fixture]:
        out: list[Fixture] = []
        n = 0
        games: list[Fixture] = [Fixture(i[0], i[1], n, self) for i in chunks_sized(self.teams_balanced, 2) if i]
        while len(games) > 1:
            out += games
            n += 1
            games = [Fixture(i.winner, j.winner, n, self) for i, j in chunks_sized(games, 2) if i or j]
        return [i for i in out if not i.bye]
