from utils.util import n_chunks
from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker
from structure.Team import BYE


class Pooled(FixtureMaker):
    def get_generator(self):
        pools = list(n_chunks(self.tournament.teams, 2))
        for pool in pools:
            if len(pool) % 2 != 0:
                pool += [BYE]
            print(pool)
        for i, _ in enumerate(pools[0]):
            fixtures = []
            for pool in pools:
                mid = len(pool) // 2
                for j in range(mid):
                    team_one = pool[j]
                    team_two = pool[len(pool) - 1 - j]
                    if team_one is None or team_two is None:
                        continue
                    match = Game(team_one, team_two, self.tournament)
                    fixtures.append(match)
                pool[1:] = [pool[-1]] + pool[1:-1]
            yield fixtures
            # Rotate the teams except the first one