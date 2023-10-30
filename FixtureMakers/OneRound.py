from typing import Generator

from FixtureMakers.FixtureMaker import FixtureMaker
from structure.Game import Game
from structure.Team import BYE


class OneRound(FixtureMaker):

    def __init__(self, tournament):
        self.dummy_game = Game(BYE, BYE, tournament)
        self.dummy_game.best_player = None
        self.dummy_game.update_count = -1
        super().__init__(tournament)

    def get_generator(self) -> Generator[list[Game], None, None]:
        while True:
            yield [self.dummy_game]

    @classmethod
    def manual_allowed(cls):
        return True
