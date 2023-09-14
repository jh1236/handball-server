from structure.Game import Game
from structure.Player import Player, GamePlayer


class Team:
    def __init__(self, name: str, players: list[Player]):
        self.name = name
        self.players: list[Player] = players
        self.teams_played: list[Team] = []
        self.points_against: int = 0
        self.points_for: int = 0
        self.games_won: int = 0
        self.games_played: int = 0
        self.tournament = None
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.timeouts: int = 0

    def get_game_team(self, game: Game):
        return GameTeam(self, game)

    def has_played(self, other):
        return other in self.teams_played

    def __repr__(self):
        return self.name

    def get_stats(self, include_players=False):
        game_teams: list[GameTeam] = []
        for i in self.tournament.fixtures.games_to_list():
            team_names = [j.name for j in i.teams]
            if i.in_progress() and self.name in team_names:
                game_teams.append(i.teams[team_names.index(self.name)])

        points_for = self.points_for + sum([i.score for i in game_teams])
        points_against = self.points_against + sum([i.opponent.score for i in game_teams])
        dif = points_for - points_against
        green_cards = self.green_cards + sum([i.green_cards for i in game_teams])
        yellow_cards = self.yellow_cards + sum([i.yellow_cards for i in game_teams])
        red_cards = self.red_cards + sum([i.red_cards for i in game_teams])
        timeouts = self.timeouts + sum([(2 - i.timeouts) for i in game_teams])
        d = {
            "Games Played": self.games_played,
            "Games Won": self.games_won,
            "Games Lost": self.games_played - self.games_won,
            "Green Cards": green_cards,
            "Yellow Cards": yellow_cards,
            "Red Cards": red_cards,
            "Timeouts Called": timeouts,
            "Points For": points_for,
            "Points Against": points_against,
            "Point Difference": dif
        }
        if include_players:
            d["players"] = [{"name": i.name} | i.get_stats() for i in self.players]
        return d

    def nice_name(self):
        return self.name.lower().replace(" ", "_")


BYE = Team("BYE", [])


class GameTeam:
    def __init__(self, team: Team, game: Game):
        self.game: Game = game
        self.opponent: GameTeam | None = None
        self.team: Team = team
        self.name: str = self.team.name
        self.players: list[GamePlayer] = [i.game_player() for i in team.players]
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.timeouts: int = 2
        self.green_carded: bool = False
        self.serving: bool = False
        self.score: int = 0
        self.swapped: bool = False
        self.first_player_serves: bool = True
        self.faulted: bool = False

    def __eq__(self, other):
        return isinstance(other, GameTeam) and other.name == self.name

    def __repr__(self):
        return repr(self.team)

    def reset(self):
        self.green_carded = False
        self.score = 0
        self.serving = False
        self.timeouts = 2
        self.green_cards = 0
        self.yellow_cards = 0
        self.red_cards = 0
        [i.reset() for i in self.players]

    def start(self, serve_first: bool, swap_players: bool):
        print(f"swapped is {swap_players}")
        self.swapped = swap_players
        # Guaranteed to work, just trust the process
        self.opponent: GameTeam = [i for i in self.game.teams if i.name != self.name][0]
        self.serving = serve_first
        self.first_player_serves = serve_first
        players = reversed(self.team.players) if swap_players else self.team.players
        self.players = [i.game_player() for i in players]

    def next_point(self):
        self.faulted = False
        [i.next_point() for i in self.players]

    def lost_point(self):
        self.serving = False

    def score_point(self, first_player: bool | None = None, ace: bool = False):
        if first_player is not None:
            self.players[not first_player].score_point(ace)
        self.score += 1
        self.opponent.lost_point()
        if not self.serving:
            self.first_player_serves = not self.first_player_serves
            self.serving = True
        if first_player is not None:
            string = "a" if ace else "s"
            string += "l" if first_player else "r"
            self.game.add_to_game_string(string, self)
        self.game.next_point()

    def fault(self):
        self.players[not self.first_player_serves].fault()
        self.game.add_to_game_string("f" + ("l" if self.first_player_serves else "r"), self)
        if self.faulted:
            self.players[not self.first_player_serves].double_fault()
            self.opponent.score_point()
        else:
            self.faulted = True

    def green_card(self, first_player: bool):
        self.green_carded = True
        self.green_cards += 1
        self.players[not first_player].green_card()
        self.game.add_to_game_string("g" + ("l" if first_player else "r"), self)

    def yellow_card(self, first_player: bool, time: int = 3):
        self.yellow_cards += 1
        self.players[not first_player].yellow_card(time)
        if time == 3:
            self.game.add_to_game_string("y" + ("l" if first_player else "r"), self)
        else:
            self.game.add_to_game_string(f"{time}{'l' if first_player else 'r'}", self)
        while all([i.is_carded() for i in self.players]) and not self.game.game_ended():
            self.opponent.score_point()

    def red_card(self, first_player: bool):
        self.red_cards += 1
        self.players[not first_player].red_card()
        self.game.add_to_game_string(f"v{'l' if first_player else 'r'}", self)
        while all([i.is_carded() for i in self.players]) and not self.game.game_ended():
            self.opponent.score_point()

    def timeout(self):
        self.game.add_to_game_string(f"tt", self)
        self.timeouts -= 1

    def card_time(self):
        if 0 > min(self.players, key=lambda a: a.card_time_remaining).card_time_remaining:
            return -1
        return max(self.players, key=lambda a: a.card_time_remaining).card_time_remaining

    def card_duration(self):
        return max(self.players, key=lambda a: a.card_time_remaining).card_duration

    def end(self):
        [i.end() for i in self.players]
        self.team.points_for += self.score
        print(self.name + " :" + str(self.opponent.score))
        self.team.points_against += self.opponent.score
        self.team.games_played += 1
        self.team.games_won += self.game.winner() == self.team
        self.team.teams_played.append(self.opponent.team)
        self.team.green_cards += self.green_cards
        self.team.yellow_cards += self.yellow_cards
        self.team.red_cards += self.red_cards
        self.team.timeouts += (2 - self.timeouts)

    def nice_name(self):
        return self.team.nice_name()

    def get_stats(self, include_players=False):
        d = {
            "Green Cards": self.green_cards,
            "Yellow Cards": self.yellow_cards,
            "Red Cards": self.red_cards,
            "Timeouts Remaining": self.timeouts
        }
        if include_players:
            d["players"] = [{"name": i.name} | i.get_stats() for i in self.players]
        return d
