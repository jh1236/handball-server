from structure import Team, Game
from tournaments.Tournament import Tournament


class RoundRobin(Tournament):
    def __init__(self, teams: list[Team]):
        super().__init__(teams)
        self.ranked_teams = teams
        self.fixtures = []
        self.draw_fixes = False

    def next_round(self):
        self.teams[1:] = [self.teams[-1]] + self.teams[1:-1]

    def rounds(self):
        return len(self.teams) - 1

    def next(self) -> Game:
        return Game(self.teams[self.count], self.teams[len(self.teams) - 1 - self.count])
