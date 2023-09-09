import json

from structure.Game import Game
from structure.Player import Player
from structure.Team import Team
from tournaments.Fixtures import Fixtures
from tournaments.RoundRobin import RoundRobin


class Tournament:
    def __init__(self):
        with open("./resources/teams.json") as fp:
            self.teams = [Team(k, [Player(i) for i in v]) for k, v in json.load(fp).items()]
        print(self.teams)
        self.fixtures: Fixtures = RoundRobin(self)

    def save(self):
        self.fixtures.save()
