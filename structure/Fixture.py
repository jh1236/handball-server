from dataclasses import dataclass

from structure.Game import Game
from structure.Team import Team

BOLD = "\033[1m"


@dataclass
class TeamPromise:
    team: Team | None
    name: str

    def __repr__(self):
        if self.team:
            return self.team.__repr__()
        else:
            return self.name


class Fixture:
    def __init__(self, team_one: Team | TeamPromise, team_two: Team| TeamPromise | None, round_number, comp):
        if team_one is None:
            team_one, team_two = team_two, team_one
        self._team_one = team_one
        self.comp = comp
        self._team_two = team_two
        self.round_number = round_number
        self.bye = team_two is None
        self.winner = TeamPromise(self.team_one() if self.bye else None, "TBA")
        self.loser = TeamPromise(None, "TBA")
        self.game = None
        if self.bye:
            self.game_over()

    def team_one(self):
        if isinstance(self._team_one, TeamPromise):
            return self._team_one.team
        else:
            return self._team_one

    def team_two(self):
        if isinstance(self._team_one, TeamPromise):
            return self._team_two.team
        else:
            return self._team_two

    def set_game(self, game: Game):
        self.game = game
        self.game.fixture = self

    def to_game(self):
        if not self.game:
            self.game = Game(self.team_one(), self.team_two())
            self.game.comp = self.comp
            self.game.fixture = self
        return self.game

    def game_over(self):
        if self.bye:
            self.winner.team = self.team_one()
        else:
            self.winner.team = self.game.winner
            self.loser.team = self.game.get_loser()

    def __repr__(self):
        if self.bye:
            return f"{self.team_one()} have a bye!"
        elif self.winner is not None:
            if self.winner:
                return f"{BOLD}{self._team_one}{BOLD} vs {self._team_two}"
            else:
                return f"{self._team_one} vs {BOLD}{self._team_two}{BOLD}"
        else:
            return f"{self._team_one} vs {self._team_two}"
