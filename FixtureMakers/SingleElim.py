import math

from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker


class SingleElim(FixtureMaker):
    def __init__(self, tournament):
        self.teams = tournament.teams
        self.games: list[Game] = []
        super().__init__(tournament)

    def get_generator(self):
        # check to see if we have a power of two number of teams
        r = []
        pre_play_offs = 2 ** round(math.log2(len(self.teams)) % 1)
        for _ in range(pre_play_offs):
            r.append(Game(self.teams.pop(), self.teams.pop(), self))
        self.games = r
        yield r
        for g in self.games:
            self.teams.append(g.winner())
        while len(self.teams) > 1:
            r = []
            while len(self.teams) > 0:
                team_one = self.teams.pop()
                team_two = self.teams.pop()

                r.append(Game(team_one, team_two, self))
            yield r
            self.games = r
            for g in self.games:
                self.teams.insert(0, g.winner())