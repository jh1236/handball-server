import json
from typing import Callable, Any

from structure.OfficiatingBody import Officials
from structure.Player import Player
from structure.Team import Team
from tournaments.Fixtures import Fixtures


class Tournament:
    def __init__(self, fixtures: Callable[[Any], Fixtures]):
        with open("./resources/teams.json") as fp:
            self.teams = [Team(k, [Player(i) for i in v]) for k, v in json.load(fp).items()]
        for i in self.teams:
            i.tournament = self
            for j in i.players:
                j.tournament = self
        self.create_fixtures = fixtures
        self.officials: Officials = Officials(self)
        self.fixtures: Fixtures = self.create_fixtures(self)
        self.load()

    def dump(self):
        self.fixtures.fixtures = []
        self.fixtures.finals = []
        self.fixtures.save()
        self.fixtures: Fixtures = self.create_fixtures(self)
        self.load()

    def save(self):
        self.fixtures.save()

    def load(self):
        for i in self.teams:
            i.reset()
        self.officials: Officials = Officials(self)
        self.fixtures = self.create_fixtures(self)
        self.fixtures.load()
