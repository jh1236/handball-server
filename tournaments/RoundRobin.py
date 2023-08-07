from structure.Fixture import Fixture
from structure.Team import Team
from tournaments.Tournament import Tournament


class RoundRobin(Tournament):
    def __init__(self, teams: list[Team]):
        self.teams_balanced = teams.copy()
        if len(self.teams_balanced) % 2 != 0:
            self.teams_balanced += [None]
        self.fixtures = []
        self.draw_fixes = False
        super().__init__(teams)

    def generate_round(self):

        for i, _ in enumerate(self.teams_balanced):
            mid = len(self.teams_balanced) // 2
            fixtures = []
            for j in range(mid):
                match = Fixture(self.teams_balanced[j], self.teams_balanced[len(self.teams_balanced) - 1 - j], i, self)
                fixtures.append(match)
            # Rotate the teams except the first one
            self.teams_balanced[1:] = [self.teams_balanced[-1]] + self.teams_balanced[1:-1]
            yield fixtures
