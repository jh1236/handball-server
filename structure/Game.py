from util import chunks_sized
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from structure.Fixture import Fixture
    from tournaments.Tournament import Tournament
    from Team import Team

GOALS_TO_WIN = 11


class Game:
    record_stats = True

    @classmethod
    def from_map(cls, map, comp, record_stats=False):
        Game.record_stats = record_stats
        team_one = [i for i in comp.teams if i.name == map["teamOne"]][0]
        team_two = [i for i in comp.teams if i.name == map["teamTwo"]][0]
        swapped = map["swapped"]
        game = Game(team_one, team_two)
        game.start(swapped, map["swapTeamOne"], map["swapTeamTwo"])
        game.comp = comp
        j: str
        for j in chunks_sized(map["game"], 2):
            team = team_one if (j[1].isupper()) else team_two
            first = j[1].upper() == 'L'
            c = j[0].lower()
            if c == 's':
                team.add_score(first)
            elif c == 'a':
                team.add_score(first, True)
            elif c == 'g':
                team.green_card(first)
            elif c == 'y':
                team.yellow_card(first)
            elif c == 'v':
                team.red_card(first)
            elif c == 't':
                team.call_timeout()
            elif c.isdigit():
                if c == '0':
                    team.yellow_card(first, 10)
                else:
                    print(int(c))
                    team.yellow_card(first, int(c))
        Game.record_stats = True
        return game

    def __init__(self, team_one, team_two):
        self.team_one: Team = team_one
        self.team_two: Team = team_two
        self.swapped: bool = False
        team_one.opponent = team_two
        team_two.opponent = team_one
        team_one.join_game(self)
        team_two.join_game(self)
        self.server: Team = team_one
        self.team_one.serving = True
        self.team_one.first = True
        self.winner: Team | None = None
        self.comp: Tournament | None = None
        self.fixture: Fixture | None = None
        self.round_count: int = 0
        self.started: bool = False
        self.game_string: str = ""

    def score(self):
        return f"{self.team_one.score} - {self.team_two.score}"

    def is_over(self):
        return (self.team_one.score >= GOALS_TO_WIN or self.team_two.score >= GOALS_TO_WIN) and \
               abs(self.team_one.score - self.team_two.score) > 1

    def start(self, swapped: bool, swap_one: bool, swap_two: bool):
        self.swapped = swapped
        if swapped:
            self.team_two.serving = True
            self.team_two.serveFirst = True
            self.team_one.serving = False
            self.team_one.serveFirst = False
            self.server = self.team_two
        else:
            self.team_two.serving = False
            self.team_two.serveFirst = False
            self.team_one.serving = True
            self.team_one.serveFirst = True
            self.server = self.team_one
        self.started = True
        self.team_one.start(swap_one)
        self.team_two.start(swap_two)

    def next_point(self):
        self.round_count += 1
        self.team_one.next_point()
        self.team_two.next_point()
        if self.is_over() and not self.winner:
            self.winner = self.get_winner()
            if Game.record_stats:
                self.winner.wins += 1
                self.get_loser().losses += 1
                self.team_one.played += 1
                self.team_two.played += 1
            if self.fixture:
                self.fixture.game_over()
            self.comp.on_game_over()

    def __repr__(self):
        return f"{self.team_one} vs {self.team_two}"

    def as_map(self):
        dct = {
            "teamOne": self.team_one.name,
            "teamTwo": self.team_two.name,
            "scoreOne": self.team_one.score,
            "scoreTwo": self.team_two.score,
            "swapTeamOne": self.team_one.swapped,
            "swapTeamTwo": self.team_two.swapped,
            "game": self.game_string,
            "started": self.started,
            "swapped": self.swapped,
        }
        if self.winner:
            dct["firstTeamWon"] = self.winner == self.team_one
        return dct

    def undo(self):
        self.game_string = self.game_string[:-2]
        print(f"'{self.game_string}'")
        self.comp.save()
        self.comp.recalc_team_stats()

    def display_map(self):
        dct = {
            "teamOne": {
                "name": self.team_one.name,
                "playerOne": self.team_one.player_one.name,
                "playerTwo": self.team_one.player_two.name,
                "score": self.team_one.score,
                "cards": self.team_one.card_timer(),
                "greenCard": self.team_one.green_carded,
                "cardDuration": self.team_one.card_duration(),
            },
            "teamTwo": {
                "name": self.team_two.name,
                "playerOne": self.team_two.player_one.name,
                "playerTwo": self.team_two.player_two.name,
                "score": self.team_two.score,
                "cards": self.team_two.card_timer(),
                "greenCard": self.team_two.green_carded,
                "cardDuration": self.team_two.card_duration(),
            },
            "firstTeamServing": self.server == self.team_one,
            "serverName": self.server.server.name,
            "game": self.game_string,
            "started": self.started,
            "rounds": self.round_count,
        }
        return dct

    def print_gamestate(self):
        print(f"         {self.team_one.__repr__():^15}| {self.team_two.__repr__():^15}")
        print(f"score   :{self.team_one.score:^15}| {self.team_two.score:^15}")
        print(f"cards   :{self.team_one.card_timer():^15}| {self.team_two.card_timer():^15}")
        print(f"timeouts:{self.team_one.timeouts_remaining:^15}| {self.team_two.timeouts_remaining:^15}")
        self.comp.save()

    def get_winner(self):
        return self.team_one if self.team_one.score > self.team_two.score else self.team_two

    def get_loser(self):
        return self.team_one if self.team_one.score < self.team_two.score else self.team_two
