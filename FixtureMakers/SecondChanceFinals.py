from typing import Generator

from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker


class SecondChanceFinals(FixtureMaker):
    def get_generator(self) -> Generator[list[Game], None, None]:
        ladder = self.tournament.ladder()
        g1 = Game(ladder[0], ladder[1], self, True)
        g2 = Game(ladder[2], ladder[3], self, True)
        yield [g1, g2]
        g3 = Game(g1.loser, g2.winner, self, True)
        yield [g3]
        yield [Game(g1.winner, g3.winner, self, True)]
