from utils.util import n_chunks
from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker
from structure.Team import BYE


class PooledFinals(FixtureMaker):
    def get_generator(self):
        pools = list(
            n_chunks(sorted(self.tournament.teams, key=lambda it: it.nice_name()), 2)
        )
        for pool in pools:
            if len(pool) % 2 != 0:
                pool += [BYE]

        pool_one = sorted(pools[0], key=lambda a: (-a.percentage, -a.point_difference))
        pool_two = sorted(pools[1], key=lambda a: (-a.percentage, -a.point_difference))
        g1 = Game(pool_one[0], pool_two[1], self.tournament, True)
        g2 = Game(pool_two[0], pool_one[1], self.tournament, True)
        yield [g1, g2]
        yield [Game(g1.winner(), g2.winner(), self.tournament, True)]
