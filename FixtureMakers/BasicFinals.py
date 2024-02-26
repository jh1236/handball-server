from typing import Generator

from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker


class BasicFinals(FixtureMaker):
    def get_generator(self) -> Generator[list[Game], None, None]:
        ladder = self.tournament.ladder()
        g1 = Game(ladder[0], ladder[3], self.tournament, True)
        g2 = Game(ladder[1], ladder[2], self.tournament, True)
        yield [g1, g2]
        yield [Game(g1.winner(), g2.winner(), self.tournament, True)]


class BasicFinalsWithBronze(FixtureMaker):
    def get_generator(self) -> Generator[list[Game], None, None]:
        ladder = self.tournament.ladder()
        g1 = Game(ladder[0], ladder[3], self.tournament, True)
        g2 = Game(ladder[1], ladder[2], self.tournament, True)
        yield [g1, g2]
        yield [Game(g1.loser(), g2.loser(), self.tournament, True),Game(g1.winner(), g2.winner(), self.tournament, True)]
