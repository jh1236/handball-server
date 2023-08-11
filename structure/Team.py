from structure.Game import Game
from structure.Player import Player


class Team:
    @classmethod
    def from_map(cls, name, map):
        left_player = Player.from_map(map["playerOne"])
        right_player = Player.from_map(map["playerTwo"])
        team = Team(name, left_player, right_player)
        team.played = map.get("played", 0)
        team.goals_for = map.get("goalsFor", 0)
        team.goals_against = map.get("goalsAgainst", 0)
        team.wins = map.get("wins", 0)
        team.losses = map.get("losses", 0)
        team.cards = map.get("cards", 0)
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
        self.goals_for: int = 0
        self.goals_against: int = 0
        self.server: Player = self.player_one
        self.teams_played = []

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
        if self.player_one.card_count == -1 or self.player_two.card_count == -1:
            return -1

        return max(self.player_one.card_count, self.player_two.card_count)

    def card_duration(self):
        if self.player_one.card_count > self.player_two.card_count:
            return self.player_one.card_duration
        else:
            return self.player_two.card_duration

    def join_game(self, game):
        self.timeouts_remaining = 2
        self.player_one.reset()
        self.player_two.reset()
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


    def add_score(self, is_left_player=None, ace=False):
        c = 'a' if ace else 's'
        if is_left_player:
            self.add_to_game_str(c + "L")
            self.player_one.score_goal(ace)
        elif is_left_player is False:
            self.add_to_game_str(c + "R")
            self.player_two.score_goal(ace)
        self.score += 1
        self.goals_for += 1
        if not self.serving:
            self.set_server()
        self.opponent.scored_against()
        self.game.next_point()

    def scored_against(self):
        self.goals_against += 1

    def as_map(self):
        dct = {
            "playerOne": self.player_one.as_map(),
            "playerTwo": self.player_two.as_map(),
            "played": self.played,
            "wins": self.wins,
            "losses": self.losses,
            "cards": self.cards,
            "timeouts": self.timeouts,
            "goalsFor": self.goals_for,
            "goalsAgainst": self.goals_against
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
            self.player_one.yellow_card(time)

        else:
            if time == 3:
                self.add_to_game_str("yR")
            else:
                self.add_to_game_str(f"{time % 10}R")
            self.player_two.yellow_card(time)

        while self.player_one.card_count != 0 and self.player_two.card_count != 0 and not self.game.is_over():
            self.opponent.add_score()

    def red_card(self, left_player):
        if Game.record_stats:
            self.cards += 1
        if left_player:
            self.add_to_game_str("vL")
            self.player_one.red_card()
        else:
            self.add_to_game_str("vR")
            self.player_two.red_card()
        while self.player_one.card_count != 0 and self.player_two.card_count != 0 and not self.game.is_over():
            self.opponent.add_score()

    def has_played(self, team):
        return team in self.teams_played

    def play_team(self, team):
        self.teams_played.append(team)


# im dumb and couldnt figure out how to put this inside the class without making a circular refrence
BYE = Team(None, Player(None), Player(None))
