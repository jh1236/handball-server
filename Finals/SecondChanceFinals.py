from structure.Game import Game


def second_chance_finals(self):
    ladder = self.ladder()
    g1 = Game(ladder[0], ladder[1], self, True)
    g2 = Game(ladder[2], ladder[3], self, True)
    yield [g1, g2]
    g3 = Game(g1.loser(), g2.winner(), self, True)
    yield [g3]
    yield [Game(g1.winner(), g3.winner(), self, True)]
