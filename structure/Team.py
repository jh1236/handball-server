from structure.Game import Game
from structure.Player import Player


class Team:
    @classmethod
    def from_map(cls, name, map):
        left_player = Player.from_map(map["leftPlayer"])
        right_player = Player.from_map(map["rightPlayer"])
        team = Team(name, left_player, right_player)
        team.played = map["played"]
        team.wins = map["wins"]
        team.losses = map["losses"]
        team.cards = map["cards"]
        team.left_player = left_player
        team.right_player = right_player
        return team

    def add_to_game_str(self, c: str):
        print(self.game.game_string)
        if self.first:
            self.game.game_string += c.upper()
        else:
            self.game.game_string += c.lower()

    def __init__(self, name: str, left: Player, right: Player):

        self.name = name
        # properties related to the current game
        self.left_card_count = 0
        self.right_card_count = 0
        self.left_card_duration = 0
        self.right_card_duration = 0
        self.score = 0
        self.game = None
        self.opponent: Team | None = None
        self.first = False
        self.serving = False
        self.green_carded = False
        self.timeouts_remaining = 2
        #

        # statistics
        self.left_player = left
        self.right_player = right
        self.played = 0
        self.wins = 0
        self.losses = 0
        self.cards = 0
        self.timeouts = 0
        self.goals_scored = 0
        self.teams_played = []

    def card_timer(self):
        if self.left_card_count == -1 or self.right_card_count == -1:
            return -1

        return max(self.left_card_count, self.right_card_count)

    def server(self):
        return self.left_player if (self.game.serve_left and not self.left_player.carded) \
                                   or self.right_player.carded else self.right_player

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

    def add_score(self, is_left_player=None, ace=False):
        c = 'a' if ace else 's'
        if is_left_player:
            self.add_to_game_str(c + "L")
            self.left_player.score_goal(ace)
        elif is_left_player is False:
            self.add_to_game_str(c + "R")
            self.right_player.score_goal(ace)
        self.score += 1
        self.goals_scored += 1
        self.game.set_server(self)
        self.game.next_point()

    def next_point(self):
        self.left_player.next_point()
        self.right_player.next_point()
        if self.left_card_count > 0:
            self.left_card_count -= 1
        else:
            self.left_card_duration = 3
        if self.right_card_count > 0:
            self.right_card_count -= 1
        else:
            self.right_card_duration = 3
        self.left_player.is_carded = self.left_card_count != 0
        self.right_player.is_carded = self.right_card_count != 0

    def as_map(self):
        dct = {
            "name": self.name,
            "leftPlayer": self.left_player.as_map(),
            "rightPlayer": self.right_player.as_map(),
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
            self.left_player.green_card()
        else:
            self.add_to_game_str("gR")
            self.right_player.green_card()

    def yellow_card(self, left_player, time=3):
        if Game.record_stats:
            self.cards += 1
        if left_player:
            if time == 3:
                self.add_to_game_str("yL")
            else:
                self.add_to_game_str(f"{time % 10}L")
            self.left_player.yellow_card()
            if self.left_card_count >= 0:
                self.left_card_count += time
                self.left_card_duration = self.left_card_count
        else:
            if time == 3:
                self.add_to_game_str("yR")
            else:
                self.add_to_game_str(f"{time % 10}R")
            self.right_player.yellow_card()
            if self.right_card_count >= 0:
                self.right_card_count += time
                self.right_card_count = self.right_card_duration
        while self.left_card_count != 0 and self.right_card_count != 0 and not self.game.is_over():
            self.opponent.add_score()

    def red_card(self, left_player):
        if Game.record_stats:
            self.cards += 1
        if left_player:
            self.add_to_game_str("vL")
            self.left_player.red_card()
            self.left_card_count = -1
        else:
            self.add_to_game_str("vR")
            self.right_player.red_card()
            self.right_card_count = -1
        while self.left_card_count != 0 and self.right_card_count != 0 and not self.game.is_over():
            self.opponent.add_score()
    
    def has_played(self, team):
        return team in self.teams_played
    
    def play_team(self, team):
        self.teams_played.append(team)
        

BYE = Team(None, Player(None), Player(None)) # im dumb and couldnt figure out how to put this inside the class without making a circular refrence