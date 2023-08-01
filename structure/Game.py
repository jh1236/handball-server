from structure.Team import Team
from tournaments.Tournament import Tournament

GOALS_TO_WIN = 11


class Game:
    def __init__(self, team_one: Team, team_two: Team):
        team_one.game = self
        team_two.game = self
        team_one.opponent = team_two
        team_two.opponent = team_one
        team_one.join_game(self)
        team_two.join_game(self)
        self.team_one = team_one
        self.team_two = team_two
        self.team_one.serving = True
        self.team_one.first = True
        self.serving = (True, True)
        self.winner: Team | None = None
        self.comp: Tournament | None = None
        self.round_count = 0
        self.game_string = ""

    def cycle_service(self):
        self.serving = (not self.serving[0], self.serving[1] if self.serving[0] else not self.serving[1])

    def is_over(self):
        return (self.team_one.score >= GOALS_TO_WIN or self.team_two.score >= GOALS_TO_WIN) and \
               abs(self.team_one.score - self.team_two.score) > 1

    def next_point(self):
        self.round_count += 1
        self.team_one.next_point()
        self.team_two.next_point()
        if self.is_over():
            self.winner = self.get_winner()
            self.winner.wins += 1
            self.get_loser().losses += 1
            self.comp.on_game_over()

    def __repr__(self):
        return f"{self.team_one} vs {self.team_two}"

    def as_map(self):
        dct = {
            "teamOne": self.team_one.name,
            "teamTwo": self.team_two.name,
            "game": self.game_string
        }
        if self.winner:
            dct["winner"] = self.winner.first
        return dct

    def print_gamestate(self):
        self.comp.save()
        print(f"         {self.team_one.__repr__():^15}| {self.team_two.__repr__():^15}")
        print(f"score   :{self.team_one.score:^15}| {self.team_two.score:^15}")
        print(f"cards   :{self.team_one.cardTimer():^15}| {self.team_two.cardTimer():^15}")
        print(f"timeouts:{self.team_one.timeouts_remaining:^15}| {self.team_two.timeouts_remaining:^15}")

    def get_winner(self):
        return self.team_one if self.team_one.score > self.team_two.score else self.team_two

    def get_loser(self):
        return self.team_one if self.team_one.score < self.team_two.score else self.team_two
