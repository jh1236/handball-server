import json

from structure.Fixture import Fixture
from structure.Team import Team
from structure.Game import Game


class Tournament:
    @classmethod
    def load(cls):

        with open("G:/Programming/python/HandballAPI/resources/teamsClean.json") as fp:
            teams = [Team.from_map(k, v) for k, v in json.load(fp).items()]
        comp = cls(teams)
        with open("G:/Programming/python/HandballAPI/resources/games.json") as fp:
            games = [Game.from_map(i, comp) for i in json.load(fp)]
        i = 0
        for i, v in enumerate(games):
            comp.fixtures[i].set_game(v)
        comp.match_count = i - 1
        comp.next_game()
        print(comp.fixtures)
        return comp

    def __init__(self, teams):
        self.current_game = None
        self.teams: list = teams
        self.ranked_teams: list = teams
        self.match_count = 0
        self.count = -1
        self.match_count = -1
        self.round = 0
        self.fixtures: list[Fixture] = self.generate_fixtures()
        self.next_game()

    def on_game_over(self):
        self.next_game()
        self.print_ladder()
        print(self.fixtures)

    def save(self):
        print("Saving...")
        with open("G:/Programming/python/HandballAPI/resources/teamsClean.json", "w+") as fp:
            json.dump({i.name: i.as_map() for i in self.teams}, fp, indent=4, sort_keys=True)
        with open("G:/Programming/python/HandballAPI/resources/games.json", "w+") as fp:
            json.dump([i.to_game().as_map() for i in self.fixtures[:self.match_count + 1] if not i.bye], fp, indent=4,
                      sort_keys=True)

    def print_ladder(self):
        for i, v in enumerate([i for i in self.ranked_teams if i], start=1):
            print(f"{i}: {v} ({v.wins} wins)")

    def generate_fixtures(self) -> [Fixture]:
        raise NotImplemented("")

    def next_game(self):
        self.match_count += 1
        self.current_game = self.fixtures[self.match_count]
        if self.current_game.bye:
            self.next_game()
        else:
            self.current_game = self.current_game.to_game()
