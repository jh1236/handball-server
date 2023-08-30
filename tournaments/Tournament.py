import json

from structure.Fixture import Fixture
from structure.Game import Game
from structure.Team import Team


class Tournament:
    @classmethod
    def load(cls):
        with open("./resources/teamsClean.json") as fp:
            teams = [Team.from_map(k, v) for k, v in json.load(fp).items()]
        comp = cls(teams)
        comp.recalc_team_stats()
        if comp.current_game.is_over():
            comp.next_game()
        print(comp.fixtures)
        return comp

    def __init__(self, teams):
        self.finals: None | list[Fixture] = None
        self.rounds: list[list[Fixture]] = []
        self.current_game: Game | None = None
        self.teams: list = teams
        self.ranked_teams: list = teams
        self.match_count = 0
        self.count = -1
        self.match_count = -1
        self.round = 0
        self.generator = self.generate_round()
        self.fixtures: list[Fixture] = []
        self.next_game()

    def on_game_over(self):
        self.next_game()
        self.print_ladder()
        print(self.fixtures)

    def recalc_team_stats(self):
        self.save()
        with open("./resources/teamsDefault.json") as fp:
            self.teams = [Team.from_map(k, v) for k, v in json.load(fp).items()]
        with open("./resources/games.json") as fp:
            games = [Game.from_map(i, self, True) for i in json.load(fp)]
        i = 0
        for i, v in enumerate(games):
            self.fixtures[i].set_game(v)
        self.match_count = i - 1
        self.next_game()
        self.match_count = i

    def save(self):
        print("Saving...")
        with open("./resources/teamsClean.json", "w+") as fp:
            json.dump({i.name: i.as_map() for i in self.teams}, fp, indent=4, sort_keys=True)
        with open("./resources/games.json", "w+") as fp:
            json.dump([i.game.as_map() for i in self.fixtures[:self.match_count + self.current_game.started] if
                       isinstance(i, Fixture) and not i.bye], fp, indent=4,
                      sort_keys=True)

    def print_ladder(self):
        for i, v in enumerate([i for i in self.ranked_teams if i], start=1):
            print(f"{i}: {v} ({v.wins} wins)")

    def get_ladder(self):
        return sorted(self.teams, key=lambda a: -a.wins)

    def next_game(self):
        self.match_count += 1
        if self.match_count >= len(self.fixtures):
            self.next_round()
        self.current_game = self.fixtures[self.match_count]
        if not isinstance(self.current_game, Fixture) or self.current_game.bye:
            self.next_game()
        else:
            self.current_game = self.current_game.game

    def next_round(self) -> [Fixture]:
        self.round += 1
        tempfixtures = next(self.generator, False)
        if not tempfixtures:
            if not self.finals:
                tempfixtures = [
                    ("FINALS", "FINALS", "FINALS"),
                    Fixture(self.get_ladder()[1], self.get_ladder()[2], self.round, self),
                    Fixture(self.get_ladder()[0], self.get_ladder()[3], self.round, self)
                ]
                self.finals = [
                    ("FINALS", "FINALS", "FINALS"),
                    Fixture(self.get_ladder()[1], self.get_ladder()[2], self.round, self),
                    Fixture(self.get_ladder()[0], self.get_ladder()[3], self.round, self)
                ]
            else:
                tempfixtures = [self.finals[0].winner, self.finals[0].winner]

        for i in tempfixtures:
            if not isinstance(i, Fixture): continue
            i.team_one.play_team(i.team_two)
            i.team_two.play_team(i.team_one)
        self.fixtures += tempfixtures
        self.rounds.append(tempfixtures)

    def generate_round(self):
        # Subclass will yield from this func
        raise NotImplementedError()
