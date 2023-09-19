import json

from structure.OfficiatingBody import Officials
from structure.Player import Player
from structure.Team import Team
from tournaments.Fixtures import Fixtures
from tournaments.Swiss import Swiss


class Tournament:
    def __init__(self):
        self.teams = []
        self.officials: Officials = None
        self.fixtures: Fixtures = None
        self.load()

    def dump(self):
        self.fixtures.dump()

    def save(self):
        self.fixtures.save()

    def load(self):
        with open("./resources/teams.json") as fp:
            self.teams = [Team(k, [Player(i) for i in v]) for k, v in json.load(fp).items()]
            for i in self.teams:
                i.tournament = self
                for j in i.players:
                    j.tournament = self
        self.officials: Officials = Officials(self)
        self.fixtures: Fixtures = Swiss(self)
