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
        for i, _ in enumerate([i for i in pools[0] if i != BYE]):
            fixtures = []
            for pool in pools:
                mid = len(pool) // 2
                for j in range(mid):
                    team_one = pool[j]
                    team_two = pool[len(pool) - 1 - j]
                    match = Game(team_one, team_two, self.tournament)
                    fixtures.append(match)
                pool[1:] = [pool[-1]] + pool[1:-1]
            yield fixtures
            # Rotate the teams except the first one
        pool_one = sorted(pools[0], key=lambda a: (-a.percentage ,-a.point_difference))
        pool_two = sorted(pools[1], key=lambda a: (-a.percentage ,-a.point_difference))
        games = [Game(p1, p2, self.tournament) for p1, p2 in zip(pool_one, pool_two[:2])]
        if BYE in pool_one and BYE in pool_two:
            pool_one = [i for i in pool_one if i != BYE]
            pool_two = [i for i in pool_two if i != BYE]
        yield games + [Game(p1, p2, self.tournament) for p1, p2 in zip(pool_one[2:], pool_two[2:])]
