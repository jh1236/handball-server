from typing import Generator

from FixtureMakers.FixtureMaker import FixtureMaker
from structure.Game import Game
from structure.Team import BYE


class OneRound(FixtureMaker):

    def __init__(self, tournament):
        self.dummy_game = Game(BYE, BYE, tournament)
        self.dummy_game.best_player = None
        self.dummy_game.update_count = -1
        self.list = [self.dummy_game]
        self.next_list = [self.dummy_game]
        super().__init__(tournament)

    def get_generator(self) -> Generator[list[Game], None, None]:
        yield self.list
        add_round = False
        while True:
            if add_round:
                self.list = self.next_list
                self.next_list = [self.dummy_game]
                add_round = yield self.list
            else:
                self.list.append(self.dummy_game)
                add_round = yield None

    @classmethod
    def manual_allowed(cls):
        return True
