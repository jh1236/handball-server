import itertools

from utils.util import n_chunks
from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker
from structure.Team import BYE



# [sf1, sf2], [3v3, 4v4, 5v5]
# [sf1, 3v3, sf2, 4v4, 5v5]

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
        games = []
        for t1, t2 in zip(pool_one[2:], pool_two[2:]):
            g = Game(t1, t2, self.tournament, True)
            if BYE not in [t1, t2]:
                g.court = 1
                games.append(g)
        yield [item for sublist in itertools.zip_longest([g1, g2], games) for item in sublist if item]
        g3 = Game(g1.loser(), g2.loser(), self.tournament, True)
        g3.court = 1
        yield [Game(g1.winner(), g2.winner(), self.tournament, True), g3]
