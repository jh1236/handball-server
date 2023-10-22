import os
import time
from typing import Any

from structure.Player import Player, GamePlayer
from utils.logging_handler import logger
from utils.util import calc_elo


class Team:
    def __init__(self, name: str, players: list[Player]):
        self.elo = 1000
        self.name = name
        self.players: list[Player] = players

        self.points_against: int = 0
        self.points_for: int = 0
        self.games_won: int = 0
        self.games_played: int = 0
        self.tournament = None
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.faults: int = 0
        self.timeouts: int = 0

        self.listed_first: int = 0
        self.court_one: int = 0
        self.has_photo = os.path.isfile(f"./resources/images/teams/{self.nice_name()}.png")

    def get_game_team(self, game):
        return GameTeam(self, game)

    def has_played(self, other):
        return other in self.teams_played

    def __repr__(self):
        return self.name

    @property
    def teams_played(self) -> list:
        if not self.tournament:
            return []
        my_games = [i for i in self.tournament.games_to_list() if self in [j.team for j in i.teams] and i.best_player]
        return [next(j.team for j in i.teams if j.team != self) for i in my_games]

    def reset(self):
        [i.reset() for i in self.players]
        self.points_against: int = 0
        self.points_for: int = 0
        self.listed_first: int = 0
        self.court_one: int = 0
        self.games_won: int = 0
        self.games_played: int = 0
        self.green_cards: int = 0
        self.elo = 1000
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.faults: int = 0
        self.timeouts: int = 0

    def get_stats(self, include_players=False):
        game_teams: list[GameTeam] = []
        for i in self.tournament.games_to_list():
            team_names = [j.name for j in i.teams]
            if i.in_progress() and self.name in team_names:
                game_teams.append(i.teams[team_names.index(self.name)])

        points_for = self.points_for + sum([i.score for i in game_teams])
        points_against = self.points_against + sum([i.opponent.score for i in game_teams])
        dif = points_for - points_against
        green_cards = self.green_cards + sum([i.green_cards for i in game_teams])
        yellow_cards = self.yellow_cards + sum([i.yellow_cards for i in game_teams])
        red_cards = self.red_cards + sum([i.red_cards for i in game_teams])
        timeouts = self.timeouts + sum([(1 - i.timeouts) for i in game_teams])
        faults = self.faults + sum([i.faults for i in game_teams])
        games_played = self.games_played + len(game_teams)
        d = {
            # "ELO": round(self.elo),
            "Games Played": games_played,
            "Games Won": self.games_won,
            "Games Lost": self.games_played - self.games_won,
            "Percentage": f"{100 * self.games_won / (self.games_played): .1f}%" if self.games_played > 0 else "-",
            "Green Cards": green_cards,
            "Yellow Cards": yellow_cards,
            "Red Cards": red_cards,
            "Faults": faults,
            "Timeouts Called": timeouts,
            "Points For": points_for,
            "Points Against": points_against,
            "Point Difference": dif,
        }
        if include_players:
            d["players"] = [{"name": i.name} | i.get_stats() for i in self.players]
        return d

    def add_stats(self, d: dict[str, Any]):
        self.games_played += d.get("Games Played", 0)
        self.games_won += d.get("Games Won", 0)
        self.green_cards += d.get("Green Cards", 0)
        self.yellow_cards += d.get("Yellow Cards", 0)
        self.red_cards += d.get("Red Cards", 0)
        self.faults += d.get("Faults", 0)
        self.timeouts += d.get("Timeouts Called", 0)
        self.points_for += d.get("Points For", 0)
        self.points_against += d.get("Points Against", 0)
        for p, i in zip(self.players, d.get("players", [])):
            p.add_stats(i)

    def nice_name(self):
        return self.name.lower().replace(" ", "_").replace("the_", "")

    def first_ratio(self):
        return self.listed_first / (self.games_played or 1)

    @classmethod
    def find_or_create(cls, tournament, name, players):
        for i in tournament.teams:
            if sorted([j.name for j in players]) == sorted([j.name for j in i.players]):
                return i
        return cls(name, players)


BYE = Team("BYE", [Player("Goodbye"), Player("Goodbye")])


class GameTeam:
    def __init__(self, team: Team, game):
        self.time_out_time = -1
        self.game = game
        self.opponent: GameTeam | None = None
        self.team: Team = team
        self.name: str = self.team.name
        self.players: list[GamePlayer] = [i.game_player(game, 1 - c) for c, i in enumerate(team.players)]
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.timeouts: int = 1
        self.green_carded: bool = False
        self.elo_delta = None
        self.serving: bool = False
        self.score: int = 0
        self.faults: int = 0
        self.swapped: bool = False
        self.first_player_serves: bool = True
        self.faulted: bool = False

    def __eq__(self, other):
        return isinstance(other, GameTeam) and other.name == self.name

    def info(self, text: str):
        if self.game.id < 0:
            return
        logger.info(f"(Game {self.game.id}) {text}")

    def __repr__(self):
        return repr(self.team)

    def reset(self):
        self.green_carded = False
        self.score = 0
        self.serving = False
        self.faulted = False
        self.timeouts = 1
        self.green_cards = 0
        self.elo_delta = None
        self.yellow_cards = 0
        self.red_cards = 0
        self.faults = 0
        self.players = [i.game_player(self.game, 1 - c) for c, i in enumerate(self.team.players)]
        if self.swapped:
            self.players.reverse()
        # [i.reset() for i in self.players]

    def start(self, serve_first: bool, swap_players: bool):
        self.swapped = swap_players
        # Guaranteed to work, just trust the process
        self.opponent: GameTeam = [i for i in self.game.teams if i.name != self.name][0]
        self.serving = serve_first
        self.first_player_serves = serve_first
        if swap_players:
            self.players.reverse()

    def next_point(self):
        self.faulted = False
        [i.next_point() for i in self.players]

    def lost_point(self):
        self.serving = False

    def score_point(self, first_player: bool | None = None, ace: bool = False):
        if ace:
            self.info(
                f"Ace Scored by {self.players[not first_player].nice_name()} from team {self.nice_name()}. Score is {self.game.score_string()}")
            if first_player is None:
                self.server().score_point(True)
            else:
                self.players[not first_player].score_point(True)
        elif first_player is not None:
            self.info(
                f"Point Scored by {self.players[not first_player].nice_name()} from team {self.nice_name()}. Score is {self.game.score_string()}")
            self.players[not first_player].score_point(False)
        else:
            self.info(f"Penalty Point Awarded to team {self.nice_name()}.  Score is {self.game.score_string()}")
        self.score += 1
        self.opponent.lost_point()
        if not self.serving:
            self.first_player_serves = not self.first_player_serves
            self.serving = True
        if first_player is not None or ace:
            string = "a" if ace else "s"
            string += "l" if first_player else "r"
            self.game.add_to_game_string(string, self)
        self.game.next_point()

    def server(self) -> GamePlayer:
        server = self.players[not self.first_player_serves]
        if server.is_carded():
            return self.players[self.first_player_serves]
        return server

    def captain(self) -> GamePlayer:
        return [i for i in self.players if i.captain][0]

    def not_captain(self) -> GamePlayer:
        return [i for i in self.players if not i.captain][0]

    def fault(self):
        self.info(f"Fault by {self.players[not self.first_player_serves].nice_name()} from team {self.nice_name()}")
        self.server().fault()
        self.game.add_to_game_string("f" + ("l" if self.first_player_serves else "r"), self)
        self.faults += 1
        if self.faulted:
            self.players[not self.first_player_serves].double_fault()
            self.opponent.score_point()
        else:
            self.faulted = True

    def green_card(self, first_player: bool):
        self.info(f"Green Card for {self.players[not first_player].nice_name()} from team {self.nice_name()}")
        self.green_carded = True
        self.green_cards += 1
        self.players[not first_player].green_card()
        self.game.add_to_game_string("g" + ("l" if first_player else "r"), self)

    def yellow_card(self, first_player: bool, time: int = 3):
        self.info(f"Yellow Card for {self.players[not first_player].nice_name()} from team {self.nice_name()}")
        self.yellow_cards += 1
        self.players[not first_player].yellow_card(time)
        if time == 3:
            self.game.add_to_game_string("y" + ("l" if first_player else "r"), self)
        else:
            self.game.add_to_game_string(f"{time % 10}{'l' if first_player else 'r'}", self)
        while all([i.is_carded() for i in self.players]) and not self.game.game_ended():
            self.opponent.score_point()

    def red_card(self, first_player: bool):
        self.info(f"Red Card for {self.players[not first_player].nice_name()} from team {self.nice_name()}")
        self.red_cards += 1
        self.players[not first_player].red_card()
        self.game.add_to_game_string(f"v{'l' if first_player else 'r'}", self)
        while all([i.is_carded() for i in self.players]) and not self.game.game_ended():
            self.opponent.score_point()

    def timeout(self):
        self.info(f"Timeout called by {self.nice_name()}")
        self.game.add_to_game_string(f"tt", self)
        self.time_out_time = time.time()
        self.timeouts -= 1

    def end_timeout(self):
        self.time_out_time = -1

    def card_time(self):
        if 0 > min(self.players, key=lambda a: a.card_time_remaining).card_time_remaining:
            return -1
        return max(self.players, key=lambda a: a.card_time_remaining).card_time_remaining

    def card_duration(self):
        return max(self.players, key=lambda a: a.card_time_remaining).card_duration

    def end(self, final=False):
        won = self.game.winner() == self.team
        [i.end(won, final) for i in self.players]
        if not final:
            self.team.points_for += self.score
            self.team.points_against += self.opponent.score
            self.team.games_played += 1
            self.team.games_won += won
            self.team.green_cards += self.green_cards
            self.team.yellow_cards += self.yellow_cards
            self.team.red_cards += self.red_cards
            self.team.faults += self.faults
            self.team.timeouts += (1 - self.timeouts)
            self.game.primary_official.green_cards += self.green_cards
            self.game.primary_official.yellow_cards += self.yellow_cards
            self.game.primary_official.red_cards += self.red_cards
            self.game.primary_official.faults += self.faults

        # either elo is not set, or it is positive, and we lost or negative, and we won
        # meaning that the result of the game was changed
        if not self.elo_delta or (self.elo_delta > 0 and not won) or (self.elo_delta < 0 and won):
            self.elo_delta = calc_elo(self.team, self.opponent.team, won)
            self.opponent.elo_delta = calc_elo(self.opponent.team, self.team, not won)
        self.team.elo += self.elo_delta

    def undo_end(self):
        [i.undo_end(self.game.winner() == self.team) for i in self.players]
        self.team.points_for -= self.score
        self.team.elo -= self.elo_delta
        self.team.points_against -= self.opponent.score
        self.team.games_played -= 1
        self.team.games_won -= self.game.winner() == self.team
        self.team.green_cards -= self.green_cards
        self.team.yellow_cards -= self.yellow_cards
        self.team.red_cards -= self.red_cards
        self.team.faults -= self.faults
        self.team.timeouts -= (1 - self.timeouts)
        self.game.primary_official.green_cards -= self.green_cards
        self.game.primary_official.yellow_cards -= self.yellow_cards
        self.game.primary_official.red_cards -= self.red_cards
        self.game.primary_official.faults -= self.faults

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
