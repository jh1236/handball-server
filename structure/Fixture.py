from structure.Game import Game
from structure.Team import Team, BYE

BOLD = "\033[1m"


class Fixture:

    def __init__(self, team_one: Team, team_two: Team | None, round_number, comp):
        if team_one is None or team_one == BYE:
            team_one, team_two = team_two, team_one
        self.team_one = team_one
        self.comp = comp
        self.team_two = team_two
        self.round_number = round_number
        self.bye = team_two is None or team_two == BYE
        self.winner = BYE
        self.loser = BYE
        self.game = Game(self.team_one, self.team_two)
        self.game.comp = self.comp
        self.game.fixture = self
        if self.bye:
            self.game_over()

    # new ver of above function to return non-html; not sure if same thing could be done with the old ver
    def fixture_to_table_row(self):
        if self.bye:
            return self.team_one, "BYE", " - "
        elif self.game is None:
            return self.team_one, self.team_two, "0 - 0"
        else:
            return self.team_one, self.team_two, self.game.score()

    def to_map(self):
        return {
            "teamOne": self.team_one.name,
            "teamTwo": self.team_two.name
        }

    def set_game(self, game: Game):
        self.game = game
        self.game.fixture = self
        if self.game.is_over():
            self.game_over()

    def __contains__(self, item):
        return item == self.team_one or item == self.team_two

    def game_over(self):
        if self.bye:
            self.winner.team = self.team_one
        else:
            self.winner.team = self.game.winner
            self.loser.team = self.game.get_loser()

    def __repr__(self):
        if self.bye:
            return f"{self.team_one} have a bye!"
        elif self.winner is not None:
            if self.winner:
                return f"{BOLD}{self.team_one}{BOLD} vs {self.team_two}"
            else:
                return f"{self.team_one} vs {BOLD}{self.team_two}{BOLD}"
        else:
            return f"{self.team_one} vs {self.team_two}"
