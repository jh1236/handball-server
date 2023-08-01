import math

from structure.Game import Game
from structure.Team import Team
from tournaments.Tournament import Tournament


class Swiss(Tournament):
    def __init__(self, teams: list[Team]):
        super().__init__(teams)
        self.n = len(teams) // 2
        self.ranked_teams: list[Team] = []

    def __len__(self):
        return len(self.teams) * math.log2(len(self.teams))

    def rounds(self):
        return math.ceil(math.log2(len(self.teams)))

    def __iter__(self):
        self.ranked_teams = sorted(self.teams, key=lambda a: -a.wins)
        return super().__iter__()

    def next_round(self):
        self.ranked_teams = sorted(self.teams, key=lambda a: -a.wins)

    def next(self):
        return Game(self.ranked_teams[self.count], self.ranked_teams[self.count + self.n])
