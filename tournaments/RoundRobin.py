from structure.Game import Game
from tournaments.FixturesOld import FixturesOld


class RoundRobin(FixturesOld):
    def __init__(self, tournament, filename):
        self.teams_balanced = tournament.teams.copy()
        if len(self.teams_balanced) % 2 != 0:
            self.teams_balanced += [None]
        self.fixtures = []
        self.draw_fixes = False
        super().__init__(tournament, filename)

    def generate_round(self):
        for i, _ in enumerate(self.teams_balanced):
            mid = len(self.teams_balanced) // 2
            fixtures = []
            for j in range(mid):
                team_one = self.teams_balanced[j]
                team_two = self.teams_balanced[len(self.teams_balanced) - 1 - j]
                if team_one is None or team_two is None:
                    continue
                match = Game(team_one, team_two, self, True)
                fixtures.append(match)
            # Rotate the teams except the first one
            self.teams_balanced[1:] = [self.teams_balanced[-1]] + self.teams_balanced[1:-1]
            yield fixtures
