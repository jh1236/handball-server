from structure.Game import Game
from structure.Player import Player


class Team:
    @classmethod
    def from_map(cls, name, map):
        left_player = Player.from_map(map["playerOne"])
        right_player = Player.from_map(map["playerTwo"])
        team = Team(name, left_player, right_player)
        team.played = map["played"]
        team.wins = map["wins"]
        team.losses = map["losses"]
        team.cards = map["cards"]
        team.player_one = left_player
        team.player_two = right_player
        return team

    def add_to_game_str(self, c: str):
        if self.first:
            self.game.game_string += c.upper()
        else:
            self.game.game_string += c.lower()

    def __init__(self, name: str, left: Player, right: Player):

        self.swapped: bool = False
        self.name = name
        # properties related to the current game
        self.left_card_count: int = 0
        self.right_card_count: int = 0
        self.left_card_duration: int = 0
        self.right_card_duration: int = 0
        self.score: int = 0
        self.game: Game | None = None
        self.opponent: Team | None = None
        self.first: bool = False
        self.serving: bool = False
        self.green_carded: bool = False
        self.timeouts_remaining: int = 2
        #

        # statistics
        self.player_one: Player = left
        self.player_two: Player = right
        self.played: int = 0
        self.wins: int = 0
        self.losses: int = 0
        self.cards: int = 0
        self.timeouts: int = 0
        self.goals_scored: int = 0
        self.server: Player = self.player_one

    def start(self, swapped=False):
        self.swapped = swapped
        if not (swapped ^ self.serving):
            self.server = self.player_two
            self.player_two.serveFirst = True
            self.player_one.serveFirst = False
        else:
            self.server = self.player_one
            self.player_two.serveFirst = True
            self.player_one.serveFirst = False

    def card_timer(self):
        if self.left_card_count == -1 or self.right_card_count == -1:
            return -1

        return max(self.left_card_count, self.right_card_count)

    def card_duration(self):
        if self.left_card_count > self.right_card_count:
            return self.left_card_duration
        else:
            return self.right_card_duration

    def join_game(self, game):
        self.timeouts_remaining = 2
        self.right_card_count = 0
        self.green_carded = False
        self.left_card_count = 0
        self.serving = False
        self.score = 0

        self.first = False
        self.game = game

    def call_timeout(self):
        self.add_to_game_str("TT")
        if Game.record_stats:
            self.timeouts += 1
        self.timeouts_remaining -= 1

    def set_server(self):
        self.game.server = self
        self.opponent.serving = False
        if self.server == self.player_one:
            self.server = self.player_two
        else:
            self.server = self.player_one

    def next_point(self):
        self.player_one.next_point()
        self.player_two.next_point()
        if self.left_card_count > 0:
            self.left_card_count -= 1
        else:
            self.left_card_duration = 3
        if self.right_card_count > 0:
            self.right_card_count -= 1
        else:
            self.right_card_duration = 3
        self.player_one.is_carded = self.left_card_count != 0
        self.player_two.is_carded = self.right_card_count != 0

    def add_score(self, is_left_player=None, ace=False):
        c = 'a' if ace else 's'
        if is_left_player:
            self.add_to_game_str(c + "L")
            self.player_one.score_goal(ace)
        elif is_left_player is False:
            self.add_to_game_str(c + "R")
            self.player_two.score_goal(ace)
        self.score += 1
        self.goals_scored += 1
        if not self.serving:
            self.set_server()
        self.game.next_point()

    def as_map(self):
        dct = {
            "name": self.name,
            "playerOne": self.player_one.as_map(),
            "playerTwo": self.player_two.as_map(),
            "played": self.played,
            "wins": self.wins,
            "losses": self.losses,
            "cards": self.cards,
            "timeouts": self.timeouts,
        }
        return dct

    def __repr__(self):
        return f"{self.name}"

    def green_card(self, left_player):
        self.green_carded = True
        if Game.record_stats:
            self.cards += 1
        if left_player:
            self.add_to_game_str("gL")
            self.player_one.green_card()
        else:
            self.add_to_game_str("gR")
            self.player_two.green_card()

    def yellow_card(self, left_player, time=3):
        if Game.record_stats:
            self.cards += 1
        if left_player:
            if time == 3:
                self.add_to_game_str("yL")
            else:
                self.add_to_game_str(f"{time % 10}L")
            self.player_one.yellow_card()
            if self.left_card_count >= 0:
                self.left_card_count += time
                self.left_card_duration = self.left_card_count
        else:
            if time == 3:
                self.add_to_game_str("yR")
            else:
                self.add_to_game_str(f"{time % 10}R")
            self.player_two.yellow_card()
            if self.right_card_count >= 0:
                self.right_card_count += time
                self.right_card_duration = self.right_card_count
        while self.left_card_count != 0 and self.right_card_count != 0 and not self.game.is_over():
            self.opponent.add_score()

    def red_card(self, left_player):
        if Game.record_stats:
            self.cards += 1
        if left_player:
            self.add_to_game_str("vL")
            self.player_one.red_card()
            self.left_card_count = -1
        else:
            self.add_to_game_str("vR")
            self.player_two.red_card()
            self.right_card_count = -1
        while self.left_card_count != 0 and self.right_card_count != 0 and not self.game.is_over():
            self.opponent.add_score()
