from util import chunks_sized

GOALS_TO_WIN = 11


class Game:
    record_stats = True

    @classmethod
    def from_map(cls, map, comp):
        Game.record_stats = False
        team_one = [i for i in comp.teams if i.name == map["teamOne"]][0]
        team_two = [i for i in comp.teams if i.name == map["teamTwo"]][0]
        game = Game(team_one, team_two)
        game.comp = comp
        j: str
        for j in chunks_sized(map["game"], 2):
            team = team_one if (j[0].isupper()) else team_two
            left = j[1] == 'L'
            c = j[0].lower()
            if c == 's':
                team.add_score(left)
            elif c == 'a':
                team.add_score(left, True)
            elif c == 'g':
                team.green_card(left)
            elif c == 'y':
                team.yellow_card(left)
            elif c == 'v':
                team.red_card(left)
            elif c == 't':
                team.call_timeout()
        Game.record_stats = True
        return game

    def __init__(self, team_one, team_two):
        self.team_one = team_one
        self.team_two = team_two
        team_one.opponent = team_two
        team_two.opponent = team_one
        team_one.join_game(self)
        team_two.join_game(self)
        self.team_one.serving = True
        self.team_one.first = True
        self.serving = (True, True)
        self.winner = None
        self.comp = None
        self.fixture = None
        self.round_count = 0
        self.started = False
        self.game_string = ""

    def cycle_service(self):
        self.serving = (not self.serving[0], self.serving[1] if self.serving[0] else not self.serving[1])

    def is_over(self):
        return (self.team_one.score >= GOALS_TO_WIN or self.team_two.score >= GOALS_TO_WIN) and \
               abs(self.team_one.score - self.team_two.score) > 1

    def swap_teams(self):
        if self.started:
            raise Exception("Teams cannot be swapped during an active game!!")
        else:
            self.team_one, self.team_two = self.team_two, self.team_one
            self.team_one.join_game(self)
            self.team_two.join_game(self)
            self.team_one.serving = True
            self.team_one.first = True

    def next_point(self):
        self.started = True
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
            "game": self.game_string,
            "started": self.started
        }
        if self.winner:
            dct["firstTeamWon"] = self.winner.first
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
