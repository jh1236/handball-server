from Finals.Finals import Finals
from structure.Game import Game


class BasicFinals(Finals):
    def __init__(self, tournament):
        super().__init__(tournament)

    def generate_round(self):
        ladder = self.tournament.fixtures.ladder()
        g1 = Game(ladder[0], ladder[3], self.tournament, True)
        g2 = Game(ladder[1], ladder[2], self.tournament, True)
        yield [g1, g2]
        yield [Game(g1.winner(), g2.winner(), self.tournament, True)]

    def get_names(self):
        return ["Semi Finals", "Grand Final"]