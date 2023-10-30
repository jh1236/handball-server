from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker


class RoundRobin(FixtureMaker):
    def get_generator(self):
        teams_balanced = self.tournament.teams.copy()
        if len(teams_balanced) % 2 != 0:
            teams_balanced += [None]
        for i, _ in enumerate(teams_balanced):
            mid = len(teams_balanced) // 2
            fixtures = []
            for j in range(mid):
                team_one = teams_balanced[j]
                team_two = teams_balanced[len(teams_balanced) - 1 - j]
                if team_one is None or team_two is None:
                    continue
                match = Game(team_one, team_two, self.tournament)
                fixtures.append(match)
            # Rotate the teams except the first one
            teams_balanced[1:] = [teams_balanced[-1]] + teams_balanced[1:-1]
            yield fixtures