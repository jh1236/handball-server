from structure.Game import Game
from structure.Player import Player, GamePlayer


class Team:
    def __init__(self, name: str, players: list[Player]):
        self.name = name
        self.players: list[Player] = players
        self.points_scored = 0
        self.games_won = 0
        self.games_played = 0
        self.teams_played = 0

    def get_game_team(self, game: Game):
        return GameTeam(self, game)

    def __repr__(self):
        return self.name


BYE = Team("BYE", [])


class GameTeam:
    def __init__(self, team: Team, game: Game):
        self.game: Game = game
        self.opponent: GameTeam | None = None
        self.team: Team = team
        self.name: str = self.team.name
        self.players: list[GamePlayer] = [i.game_player() for i in team.players]

        self.green_carded: bool = False
        self.serving: bool = False
        self.score: int = 0
        self.time_outs: int = 2
        self.swapped: bool = False
        self.first_player_serves: bool = True

    def __eq__(self, other):
        return isinstance(other, GameTeam) and other.name == self.name

    def __repr__(self):
        return repr(self.team)

    def reset(self):
        self.green_carded = False
        self.score = 0
        self.serving = False
        self.time_outs = 2
        [i.reset() for i in self.players]

    def start(self, serve_first: bool, swap_players: bool):
        print(f"swapped is {swap_players}")
        self.swapped = swap_players
        # Guaranteed to work, just trust the process
        self.opponent: GameTeam = [i for i in self.game.teams if i != self][0]
        self.serving = serve_first
        self.first_player_serves = serve_first
        players = reversed(self.team.players) if swap_players else self.team.players
        self.players = [i.game_player() for i in players]

    def next_point(self):
        [i.next_point() for i in self.players]

    def lost_point(self):
        self.serving = False

    def score_point(self, left_player: bool | None = None, ace: bool = False):
        if left_player is not None:
            self.players[left_player].score_point(ace)
        self.score += 1
        self.opponent.lost_point()
        if not self.serving:
            self.first_player_serves = not self.first_player_serves
            self.serving = True
        if left_player is not None:
            string = "a" if ace else "s"
            string += "l" if left_player else "r"
            self.game.add_to_game_string(string, self)
        self.game.next_point()

    def green_card(self, left_player: bool):
        self.green_carded = True
        self.players[left_player].green_card()
        self.game.add_to_game_string("g" + ("l" if left_player else "r"), self)

    def yellow_card(self, left_player: bool, time: int = 3):
        self.players[left_player].yellow_card(time)
        if time == 3:
            self.game.add_to_game_string("y" + ("l" if left_player else "r"), self)
        else:
            self.game.add_to_game_string(f"{time}{'l' if left_player else 'r'}", self)
        while all([i.is_carded() for i in self.players]):
            self.opponent.score_point()

    def red_card(self, left_player: bool):
        self.players[left_player].red_card()
        self.game.add_to_game_string(f"v{'l' if left_player else 'r'}", self)
        while all([i.is_carded() for i in self.players]) and not self.game.game_ended():
            self.opponent.score_point()

    def timeout(self):
        self.game.add_to_game_string(f"tt", self)
        self.time_outs -= 1

    def card_time(self):
        if 0 > min(self.players, key=lambda a: a.card_time_remaining).card_time_remaining:
            return -1
        return max(self.players, key=lambda a: a.card_time_remaining).card_time_remaining

    def card_duration(self):
        return max(self.players, key=lambda a: a.card_time_remaining).card_duration
