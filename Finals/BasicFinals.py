from Finals.Finals import Finals
from structure.Game import Game


def basic_finals(tournament):
    ladder = tournament.ladder()
    g1 = Game(ladder[0], ladder[3], tournament, True)
    g2 = Game(ladder[1], ladder[2], tournament, True)
    yield [g1, g2]
    yield [Game(g1.winner(), g2.winner(), tournament, True)]
