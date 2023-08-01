from structure.Game import Game
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

    def matches_per_round(self):
        return len(self.teams_balanced) // 2

    def next_round(self):
        self.teams_balanced[1:] = [self.teams_balanced[-1]] + self.teams_balanced[1:-1]

    def rounds(self):
        return len(self.teams_balanced) - 1

    def next(self) -> Game | None:
        team_one = self.teams_balanced[self.count]
        team_two = self.teams_balanced[len(self.teams_balanced) - 1 - self.count]
        if not team_one or not team_two:
            return None
        return Game(team_one, team_two)
