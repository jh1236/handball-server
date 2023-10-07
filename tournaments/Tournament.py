from typing import Callable, Any

from tournaments.Fixtures import Fixtures


class Tournament:
    def __init__(self, fixtures: Callable[[Any], Fixtures]):

        self.create_fixtures = fixtures
        self.fixtures: Fixtures = self.create_fixtures(self)

    def dump(self):
        self.fixtures.fixtures = []
        self.fixtures.finals = []
        self.fixtures.save()
        self.fixtures: Fixtures = self.create_fixtures(self)

    def save(self):
        self.fixtures.save()

    def load(self):
        for i in self.teams:
            i.reset()
        self.fixtures = self.create_fixtures(self)
