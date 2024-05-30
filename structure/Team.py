import os
import re
import threading
import time
from typing import TYPE_CHECKING

from structure.Player import Player, GamePlayer
from utils.logging_handler import logger
from utils.statistics import calc_elo, team_stats
from utils.util import google_image

if TYPE_CHECKING:
    from structure.Tournament import Tournament
    from structure.Game import Game
    from structure.Card import Card

images = {}
team_names = {}
start_time = time.time()


class Team:
    def __init__(self, name: str, players: list[Player]):
        self.tried_search: bool = False
        self.name: str = name
        self.players: list[Player] = players
        self.tournament: "Tournament" = None

        self.primary_color: str = "None/Unknown"
        self.secondary_color: str = "None/Unknown"

        self.listed_first: int = 0
        self.court_one: int = 0
        self.has_photo: bool = os.path.isfile(
            f"./resources/images/teams/{self.nice_name()}.png"
        )
        self.image_path: str = (
            f"/api/teams/image?name={self.nice_name()}" if self.has_photo else None
        )
        team_names[tuple(sorted(i.nice_name() for i in players))] = self.name

    def get_game_team(self, game) -> "GameTeam":
        return GameTeam(self, game)

    @property
    def percentage(self) -> float:
        return self.get_stats()["Games Won"] / (self.get_stats()["Games Played"] or 1)

    @property
    def cards(self) -> int:
        return (
            self.get_stats()["Green Cards"]
            + self.get_stats()["Red Cards"]
            + self.get_stats()["Yellow Cards"]
        )

    def helper(self) -> None:
        self.image_path = google_image(self.name)
        images[self.name] = self.image_path

    def image(self) -> str:
        if (
            not self.image_path
            and time.time() - start_time > 600
            and not self.tried_search
        ):
            self.tried_search = True
            if self.name in images:
                self.image_path = images[self.name]
            else:
                threading.Thread(target=self.helper).start()
        return self.image_path or f"/api/teams/image?name=blank"

    @property
    def point_difference(self) -> int:
        return self.get_stats()["Point Difference"]

    @property
    def games_played(self) -> int:
        return self.get_stats()["Games Played"]

    @property
    def captain(self) -> Player:
        return self.players[0]

    @property
    def non_captain(self) -> Player:
        return self.players[1]

    def has_played(self, other) -> bool:
        return other in self.teams_played

    def __repr__(self) -> str:
        return self.name

    @property
    def teams_played(self) -> list["Team"]:
        if "bye" in self.nice_name():
            games = []
            for i in self.tournament.games_to_list():
                if not i.bye:
                    continue
                games.append(i)
            return [next(j.team for j in i.teams if j.team != self) for i in games]
        elif not self.tournament:
            return []
        else:
            games = []
            for i in self.tournament.games_to_list():
                if not self in [j.team for j in i.teams]:
                    continue
                games.append(i)
            return [next(j.team for j in i.teams if j.team != self) for i in games]

    @property
    def elo(self) -> float:
        true_players = [i.elo for i in self.players if "null" not in i.nice_name()]
        return round(sum(true_players) / (len(true_players) or 1), 2)

    def get_stats(self, include_players=False) -> dict[str, object]:
        return team_stats(self.tournament, self, include_players)

    def nice_name(self) -> str:
        s = self.name.lower().replace(" ", "_").replace(",", "").replace("the_", "")
        return re.sub("[^a-zA-Z0-9_]", "", s)

    @property
    def short_name(self) -> str:
        if len(self.name) > 30:
            return self.name[:27] + "..."
        else:
            return self.name

    def first_ratio(self) -> float:
        if "bye" in self.nice_name():
            return 999.0
        return self.listed_first / (self.get_stats()["Games Played"] or 1)

    @classmethod
    def find_or_create(cls, tournament, name, players) -> "Team":
        if tournament:
            for i in tournament.teams:
                if sorted([j.name for j in players]) == sorted(
                    [j.name for j in i.players]
                ):
                    return i
        key = tuple(sorted(i.nice_name() for i in players))
        if len([i for i in players if not "null" in i.nice_name()]) == 1:
            name = "(Solo) " + next(i for i in players if "null" not in i.nice_name()).name
        elif key in team_names:
            name = team_names[key]
        if not name.strip():
            raise NameError("Team name is not valid!")
        t = cls(name, players)
        t.tournament = tournament
        return t


class GameTeam:
    def __init__(self, team: Team, game: "Game"):
        self.start_players: list[Player] = []
        self.time_out_time: float = -1
        self.game: Game = game
        self.opponent: GameTeam | None = None
        self.team: Team = team
        self.name: str = self.team.name
        self.players: list[GamePlayer] = [
            i.game_player(game, self, 1 - c) for c, i in enumerate(team.players)
        ]
        self.has_sub: bool = len(self.players) > 2
        if self.has_sub:
            self.players[2].started_sub = True
        self.has_subbed: bool = False
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.elo_at_start: float = self.team.elo
        self.red_cards: int = 0
        self.timeouts: int = 1
        self.green_carded: bool = False
        self.elo_delta: float | None = None
        self.serving: bool = False
        self.score: int = 0
        self.faults: int = 0
        self.swapped: bool = False
        self.first_player_serves: bool = True
        self.faulted: bool = False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, GameTeam) and other.name == self.name

    def image(self) -> str:
        return self.team.image()

    def __repr__(self) -> str:
        return repr(self.team)

    @property
    def carded(self) -> bool:
        return any(i.is_carded() for i in self.players)

    @property
    def playing_players(self) -> list[GamePlayer]:
        if self.game.rounds:
            return [i for i in self.players if i.time_on_court]
        else:
            return self.players

    @property
    def current_players(self) -> list[GamePlayer]:
        if len(self.players) > 2:
            return self.players[:2]
        return self.players

    def reset(self) -> None:
        if self.elo_delta:
            self.change_elo(-self.elo_delta, self.game)
            self.elo_delta = None
        self.green_carded = False
        self.has_subbed: bool = False
        self.score = 0
        self.serving = False
        self.faulted = False
        self.timeouts = 1
        self.green_cards = 0
        self.yellow_cards = 0
        self.red_cards = 0
        self.faults = 0
        self.players = [
            i.game_player(self.game, self, 1 - c > 0)
            for c, i in enumerate(self.team.players)
        ]
        self.has_sub = len(self.players) > 2
        if self.swapped:
            self.players[0], self.players[1] = self.players[1], self.players[0]
        self.start_players = self.players.copy()
        # [i.reset() for i in self.players]

    def start(self, serve_first: bool, swap_players: bool) -> None:
        self.swapped = swap_players
        # Guaranteed to work, just trust the process
        self.opponent: GameTeam = [
            i for i in self.game.teams if i.nice_name() != self.nice_name()
        ][0]
        self.serving = serve_first
        self.first_player_serves = serve_first
        self.elo_at_start = self.team.elo
        if self.swapped:
            self.players[0], self.players[1] = self.players[1], self.players[0]
            self.start_players = [self.players[1], self.players[0]]
        else:
            self.start_players = [*self.players]

    def cards(self) -> list["Card"]:
        return sorted(
            [item for sublist in self.players for item in sublist.player.cards],
            key=lambda it: -it.sort_key,
        )

    def forfeit(self) -> None:
        self.game.add_to_game_string("ee", self)
        while not self.game.game_ended:
            self.opponent.score_point()

    def change_elo(self, delta: float, a: "Game") -> None:
        for i in self.players:
            if i.time_on_court:
                i.change_elo(delta, a)

    def next_point(self) -> None:
        self.faulted = False
        [i.next_point() for i in self.players[:2]]

    def lost_point(self) -> None:
        if self.serving:
            server_side = self.server().nice_name() == self.players[0].nice_name()
            self.server().points_served += 1
            self.server().serve_streak[-1] += 1
            self.server().serve_streak.append(0)
            if self.server().ace_streak[-1]:
                self.server().ace_streak.append(0)
            # if you were serving and the other team won the point, they obviously returned the point
            self.opponent.players[not server_side].serves_received += 1
            self.opponent.players[not server_side].serve_return += 1
        self.serving = False

    def sub_player(self, first_player: bool) -> None:
        self.players[not first_player].subbed_off = True
        self.has_subbed = True
        self.players[2].subbed_on = True
        self.players[not first_player], self.players[2] = (
            self.players[2],
            self.players[not first_player],
        )
        self.game.add_to_game_string("x" + ("l" if first_player else "r"), self)
        self.game.event()
        self.has_sub = False
        if any(i.nice_name().startswith("null") for i in self.players[:2]):
            self.game.ranked = False

    @property
    def all_players(self) -> list[GamePlayer]:
        return [
            i
            for i in self.players
            if (not i.started_sub or i.started_sub and i.subbed_on)
            and not "null" in i.nice_name()
        ]

    def score_point(self, first_player: bool | None = None, ace: bool = False) -> None:
        if ace:
            if first_player is None:
                self.server().score_point(True)
            else:
                self.players[not first_player].score_point(True)
            self.server().ace_streak[-1] += 1
        elif first_player is not None:
            self.players[not first_player].score_point(False)
        else:
            if self.server().ace_streak[-1]:
                self.server().ace_streak.append(0)
        self.score += 1
        if self.serving and (first_player is not None or ace):
            server_side = self.server().nice_name() == self.players[0].nice_name()
            self.server().points_served += 1
            self.server().serve_streak[-1] += 1
            self.server().won_while_serving += 1
            self.opponent.players[not server_side].serves_received += 1
            self.opponent.players[not server_side].serve_return += not ace
        self.game.next_point()
        self.opponent.lost_point()
        if not self.serving:
            self.first_player_serves = not self.first_player_serves
            self.serving = True

        if first_player is not None or ace:
            string = "a" if ace else "s"
            string += "l" if first_player else "r"
            self.game.add_to_game_string(string, self)

    def server(self) -> GamePlayer:
        server = self.players[not self.first_player_serves]
        if server.is_carded():
            return self.players[self.first_player_serves]
        return server

    def captain(self) -> GamePlayer:
        return [i for i in self.players if i.captain][0]

    def not_captain(self) -> GamePlayer:
        return [i for i in self.players if not i.captain[:2]][0]

    def fault(self) -> None:
        self.server().fault()
        self.game.add_to_game_string(
            "f" + ("l" if self.first_player_serves else "r"), self
        )
        self.faults += 1
        self.game.update_count += 1
        if self.faulted:
            self.server().double_fault()
            self.opponent.score_point()
        else:
            self.faulted = True

    def green_card(self, first_player: bool) -> None:
        self.game.update_count += 1
        self.green_carded = True
        self.green_cards += 1
        self.players[not first_player].green_card()
        self.game.add_to_game_string("g" + ("l" if first_player else "r"), self)

    def yellow_card(self, first_player: bool, time: int = 3) -> None:
        self.game.update_count += 1
        self.yellow_cards += 1
        self.players[not first_player].yellow_card(time)
        if time == 3:
            self.game.add_to_game_string("y" + ("l" if first_player else "r"), self)
        else:
            self.game.add_to_game_string(
                f"{time % 10}{'l' if first_player else 'r'}", self
            )
        while (
            all([i.is_carded() for i in self.players[:2]]) and not self.game.game_ended
        ):
            self.opponent.score_point()

    def red_card(self, first_player: bool) -> None:
        player = self.players[not first_player]
        if "null" in player.nice_name():
            return
        self.red_cards += 1
        self.game.update_count += 1
        player.red_card()
        self.game.add_to_game_string(f"v{'l' if first_player else 'r'}", self)
        while (
            all([i.is_carded() for i in self.players[:2]]) and not self.game.game_ended
        ):
            self.opponent.score_point()

    def timeout(self) -> None:
        self.game.add_to_game_string(f"tt", self)
        self.time_out_time = time.time()
        self.game.event()
        self.timeouts -= 1

    def end_timeout(self) -> None:
        self.time_out_time = -1
        self.game.event()

    def card_time(self) -> int:
        players = [i for i in self.players if "null" not in i.nice_name()]
        if 0 > min(players, key=lambda a: a.card_time_remaining).card_time_remaining:
            return -1
        return max(players, key=lambda a: a.card_time_remaining).card_time_remaining

    def card_duration(self) -> int:
        players = [i for i in self.players if "null" not in i.nice_name()]
        return max(players, key=lambda a: a.card_time_remaining).card_duration

    def end(self, final: bool = False) -> None:
        if final:
            return
        if self.elo_delta:
            Exception("game ended twice!")
        won = self.game.winner == self.team
        [i.end(won, final) for i in self.players]
        self.game.primary_official.green_cards += self.green_cards
        self.game.primary_official.yellow_cards += self.yellow_cards
        self.game.primary_official.red_cards += self.red_cards
        self.game.primary_official.faults += self.faults

        # either elo is not set, or it is positive, and we lost or negative, and we won
        # meaning that the result of the game was changed
        if not self.game.ranked:
            return
        if not self.elo_delta:
            self.elo_delta = calc_elo(
                self.elo_at_start, self.opponent.elo_at_start, won
            )
            self.change_elo(self.elo_delta, self.game)

    def undo_end(self) -> None:
        [i.undo_end(self.game.winner == self.team) for i in self.players]
        if self.elo_delta:
            self.change_elo(-self.elo_delta, self.game)
        self.elo_delta = None
        self.game.primary_official.green_cards -= self.green_cards
        self.game.primary_official.yellow_cards -= self.yellow_cards
        self.game.primary_official.red_cards -= self.red_cards
        self.game.primary_official.faults -= self.faults

    def nice_name(self) -> str:
        return self.team.nice_name()

    @property
    def short_name(self) -> str:
        return self.team.short_name

    def get_stats(self, include_players: bool = False) -> dict[str, object]:
        d = {
            "Green Cards": self.green_cards,
            "Yellow Cards": self.yellow_cards,
            "Red Cards": self.red_cards,
            "Timeouts Remaining": self.timeouts,
        }
        if include_players:
            d["players"] = [{"name": i.name} | i.get_stats() for i in self.players]
        return d

    def swap_players(self, from_load: bool = False) -> None:
        self.game.add_to_game_string("!u", self)
        self.game.event()
        self.players[0], self.players[1] = self.players[1], self.players[0]
        if not from_load:
            self.game.reload()
