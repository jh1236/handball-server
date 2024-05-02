import time
import typing

from structure.OfficiatingBody import NoOfficial, Official
from structure.Player import GamePlayer, Player, forfeit_player
from structure.Team import Team
from utils.logging_handler import logger
from utils.util import chunks_sized

if typing.TYPE_CHECKING:
    from structure.Team import GameTeam
    from structure.Card import Card

RANK_SOLO_GAMES = False


class Game:
    @classmethod
    def from_map(cls, game_map, tournament, final=False):
        if game_map["teamOne"]["name"] == "BYE":
            team_one = tournament.BYE
        else:
            team_one = [
                i for i in tournament.teams if i.name == game_map["teamOne"]["name"]
            ]
            if not team_one:
                team_one = Team.find_or_create(
                    tournament,
                    game_map["teamOne"]["name"],
                    [
                        Player(i).set_tournament(tournament)
                        for i in game_map["teamOne"]["players"]
                    ],
                )
            else:
                team_one = team_one[0]
        if game_map["teamTwo"]["name"] == "BYE":
            team_two = tournament.BYE
        else:
            team_two = [
                i for i in tournament.teams if i.name == game_map["teamTwo"]["name"]
            ]
            if not team_two:
                team_two = Team.find_or_create(
                    tournament,
                    game_map["teamTwo"]["name"],
                    [
                        Player(i).set_tournament(tournament)
                        for i in game_map["teamTwo"]["players"]
                    ],
                )
            else:
                team_two = team_two[0]
        swapped = game_map["firstTeamServed"]
        game = Game(team_one, team_two, tournament, final, attempt_rebalance=False)
        if game.bye or game.super_bye:
            game.start(None, None, None)
            return game

        team_one_swap = team_one.players[0].name != game_map["teamOne"]["players"][0]
        team_two_swap = team_two.players[0].name != game_map["teamTwo"]["players"][0]
        if game_map["official"] == "No one":
            game.set_primary_official(NoOfficial)
        else:
            game.set_primary_official(
                (
                    [i for i in tournament.officials if i.name == game_map["official"]]
                    + [NoOfficial]
                )[0]
            )
        if game_map.get("scorer", "No one") != "No one":
            game.set_scorer(
                (
                    [i for i in tournament.officials if i.name == game_map["scorer"]]
                    + [NoOfficial]
                )[0]
            )
        game.court = game_map["court"]
        game.id = game_map["id"]
        if not game_map["started"]:
            return game
        game.start(swapped, team_one_swap, team_two_swap)
        game.load_from_string(game_map["game"])
        game.start_time = game_map.get("startTime", -1)
        if game_map.get("bestPlayer", False):
            game.end(
                game_map["bestPlayer"],
                game_map.get("cards", None),
                game_map.get("notes", None),
            )
            game.protested = game_map.get("protested", 0)
            game.resolved = game_map.get("resolved", False)
            game.length = game_map.get("length", -1)

        return game

    def __init__(
        self,
        team_one,
        team_two,
        tournament,
        final: bool = False,
        attempt_rebalance: bool = True,
    ):
        self.start_time: float = -1
        self.length: float = -1
        self.resolved: bool = False
        self._serve_clock: int = -1
        self.update_count: int = 0
        self.tournament = tournament
        self.id: int = -1
        self.court: int = -1
        self.protested = None
        self.game_string: str = ""
        self.rounds: int = 0
        self.started: bool = False
        self.super_bye = False
        self.best_player: GamePlayer | None = None
        self.notes: str = ""
        self.teams: list[GameTeam] = [
            team_one.get_game_team(self),
            team_two.get_game_team(self),
        ]
        self.is_final: bool = final
        self.bye: bool = False
        if (
            attempt_rebalance
            and not final
            and self.teams[0].team.first_ratio() > self.teams[1].team.first_ratio()
        ):
            self.teams.reverse()
        if team_one not in tournament.teams:
            self.tournament.add_team(team_one)
        if team_two not in tournament.teams:
            self.tournament.add_team(team_two)
        if "bye" in [i.nice_name() for i in self.teams]:
            self.bye = True
            self.teams = (
                [i for i in self.teams if "bye" not in i.nice_name()]
                + [
                    tournament.BYE.get_game_team(self),
                    tournament.BYE.get_game_team(self),
                ]
            )[0:2]
            self.started = False
            self.best_player = self.teams[1].players[0]
            if "bye" not in self.teams[0].nice_name():
                self.update_count = -1
                self.teams[0].score = 11
            else:
                self.super_bye = True
        self.ranked: bool = True
        self.first_team_serves: bool = False
        self.primary_official: Official = NoOfficial
        self.scorer: Official = NoOfficial
        self.round_number: int = 0
        self.cards: list[Card] = []
        self.is_solo: bool = all(len(i.all_players) == 1 for i in self.teams)

    @property
    def serve_clock(self):
        if time.time() - self._serve_clock > 8:
            self._serve_clock = -1
        return self._serve_clock

    @property
    def nice_start_time(self):
        return time.strftime("%d/%m/%y (%H:%M)", time.localtime(self.start_time))

    @property
    def nice_game_length(self):
        hours, minutes = divmod(self.length, 3600)
        minutes, seconds = divmod(minutes, 60)
        seconds = int(seconds)
        if hours > 0:
            return f"{int(hours)}:{int(minutes):2}:{seconds:2}"
        else:
            return f"{int(minutes):2}:{int(seconds):2}"

    @property
    def requires_action_string(self):
        if self.resolved:
            return "Resolved"
        return self.noteable_string(False)

    @property
    def court_display(self) -> str:
        if self.court > -1:
            return f"Court {self.court + 1}"
        return "-"

    @property
    def requires_action(self):
        return (
            self.protested
            or any(i.red_cards for i in self.all_players if "null" not in i.nice_name())
            or self.notes.strip()
        ) and not self.resolved

    @property
    def is_noteable(self):
        return (
            self.protested
            or any(i.red_cards for i in self.all_players if "null" not in i.nice_name())
            or self.notes.strip()
        )

    @property
    def winner(self):
        if self.bye:
            return self.teams[0]
        return max(self.teams, key=lambda a: a.score).team

    @property
    def loser(self):
        if self.bye:
            return self.teams[1]
        return min(self.teams, key=lambda a: a.score).team

    @property
    def team_serving(self):
        if self.bye or not self.started:
            return None
        return [i for i in self.teams if i.serving][0]

    @property
    def server(self):
        if self.bye or not self.started:
            return None
        serving_team = self.team_serving

        server = serving_team.players[not serving_team.first_player_serves]
        if server.is_carded():
            server = serving_team.players[serving_team.first_player_serves]
        return server

    @property
    def server_side(self):
        if self.bye or not self.started:
            return None
        return ["Left", "Right"][not self.team_serving.first_player_serves]

    @property
    def current_players(self) -> list[GamePlayer]:
        if self.bye:
            return [
                *self.teams[0].players,
                self.teams[1].players[0],
                self.teams[1].players[0],
            ]
        return self.teams[0].current_players + self.teams[1].current_players

    @property
    def playing_players(self) -> list[GamePlayer]:
        if self.rounds:
            return self.teams[0].playing_players + self.teams[1].playing_players
        else:
            return self.current_players

    @property
    def all_players(self):
        return self.teams[0].all_players + self.teams[1].all_players


    @property
    def in_progress(self):
        if self.bye:
            return False
        return self.started and not self.best_player

    @property
    def in_timeout(self):
        return any([i.time_out_time > 0 for i in self.teams])

    @property
    def game_ended(self):
        if self.bye:
            return True
        return (
            max([i.score for i in self.teams]) >= 11
            and abs(self.teams[0].score - self.teams[1].score) >= 2
        )

    @property
    def match_points(self):
        delta_score = abs(self.teams[0].score - self.teams[1].score)
        return (
            delta_score
            if delta_score >= 1 and max(self.teams, key=lambda a: a.score).score >= 10
            else -1
        )

    @property
    def score_string(self):
        if self.bye or not self.started:
            return "-"
        return f"{self.teams[0].score} - {self.teams[1].score}"

    @property
    def full_name(self):
        if self.started:
            return repr(self) + f" ({self.score_string}) [{self.tournament.name}]"
        return repr(self) + f" [{self.tournament.name}]"

    @property
    def is_forfeited(self):
        return self.game_string[-2:].lower() == "ee"

    def swap_serve(self):
        self.team_serving.first_player_serves = (
            not self.team_serving.first_player_serves
        )
        self.add_to_game_string("!h", self.team_serving)
        self.event()

    def swap_serve_team(self):
        not_serving = next(i for i in self.teams if not i == self.team_serving)
        self.teams[0].first_player_serves, self.teams[1].first_player_serves = (
            self.teams[1].first_player_serves,
            self.teams[0].first_player_serves,
        )
        self.team_serving.serving = False
        not_serving.serving = True
        self.add_to_game_string("!w", self.team_serving)
        self.event()

    def event(self):
        if not self.bye:
            self.update_count += 1

    def noteable_string(self, include_yellows):
        if self.protested:
            return "Protested"
        elif any(i.red_cards for i in self.all_players if "null" not in i.nice_name()):
            return "Red card awarded"
        elif any(i.yellow_cards for i in self.teams) and include_yellows:
            return "Yellow card awarded"
        elif self.notes.strip():
            return "Notes to review"
        elif "!" in self.game_string:
            return "Scorer Correction Present"
        elif self.is_forfeited:
            return "Forfeited"
        elif self.best_player:
            return "Official"
        elif self.protested is not None:
            return "Finished"
        elif self.in_timeout:
            return "In timeout"
        elif self.started:
            return "Game in progress"
        else:
            return "Waiting for toss"

    def set_primary_official(self, o):
        if self.bye:
            raise LookupError(f"Game {self.id} is a bye!")
        o.internal_games_umpired += 1
        self.primary_official = o

    def set_scorer(self, o):
        if self.bye:
            raise LookupError(f"Game {self.id} is a bye!")
        if self.scorer == o:
            return
        self.scorer = o
        if self.primary_official != o:
            o.internal_games_scored += 1

    def add_to_game_string(self, string: str, team):
        if team == self.teams[0]:
            self.game_string += string.upper()
        else:
            self.game_string += string.lower()

    def bye_check(self):
        if self.bye or self.super_bye:
            raise LookupError(f"Game {self.id} is a bye!")

    def next_point(self):
        self.bye_check()
        self.event()
        self.rounds += 1
        [i.next_point() for i in self.teams]

    def print_gamestate(self):
        logger.info(
            f"         {self.teams[0].__repr__():^15}| {self.teams[1].__repr__():^15}"
        )
        logger.info(f"score   :{self.teams[0].score:^15}| {self.teams[1].score:^15}")
        logger.info(
            f"cards   :{self.teams[0].card_time():^15}| {self.teams[1].card_time():^15}"
        )
        logger.info(
            f"timeouts:{self.teams[0].timeouts:^15}| {self.teams[1].timeouts:^15}"
        )

    def start(self, team_one_serves, swap_team_one, swap_team_two):
        self.started = True
        if self.start_time < 0:
            self.start_time = time.time()
        if self.bye:
            return
        self.update_count += 1
        self.teams[0].start(team_one_serves, swap_team_one)
        self.teams[1].start(not team_one_serves, swap_team_two)
        self.first_team_serves = team_one_serves
        self.info(
            f"Started, {self.server.nice_name()} serving from team {self.team_serving.nice_name()}"
        )

    def end(
        self,
        best_player: str,
        card_reasons: list[str] | None = None,
        notes: str | None = None,
    ):
        self.ranked = (
            all(len(i.all_players) > 1 for i in self.teams)
            and not self.is_final
            and (
                not any(i.nice_name().startswith("null") for i in self.current_players)
                or RANK_SOLO_GAMES
            )
            and self.tournament.details.get("ranked", True)
        )
        if self.best_player is not None:
            return
        self.bye_check()
        if self.game_ended:
            if self.best_player:
                [i.undo_end() for i in self.teams]
                self.primary_official.games_umpired -= 1
                self.scorer.games_scored -= 1
                self.primary_official.rounds_umpired -= self.rounds
            if not self.is_final:
                self.teams[0].team.listed_first += 1
                if self.court == 0:
                    for i in self.teams:
                        i.team.court_one += 1
                    self.primary_official.games_court_one += 1

            if card_reasons:
                for i, val in enumerate(card_reasons):
                    if val and i < len(self.cards):
                        self.cards[i].reason = val
            if notes:
                self.notes = notes
            self.best_player = None

            for i in self.current_players:
                if i.name == best_player:
                    self.best_player = i
                    i.best_player()
                    break
            if self.is_forfeited and self.best_player is None:
                self.best_player = forfeit_player(self)
            elif all(len(i.all_players) == 1 for i in self.teams):
                self.best_player = [i for i in self.teams[0].players + self.teams[1].players if "null" in i.nice_name()][0]
            elif self.best_player is None:
                raise Exception(f"Best Player '{best_player}' not found")
            self.update_count = -1
            [i.end(self.is_final) for i in self.teams]
            self.primary_official.games_umpired += 1
            self.scorer.games_scored += 1
            self.primary_official.rounds_umpired += self.rounds
            self.info(
                f"game {self.id} is over! Winner was {self.winner.nice_name()}, Best Player is {self.best_player.nice_name()}"
            )
            self.length = time.time() - self.start_time
            self.tournament.update_games()

    def undo(self):
        self.bye_check()
        if not self.started:
            if not self.tournament.fixtures_class.manual_allowed():
                raise Exception("Tournament can not be edited!")
            self.tournament.fixtures[-1].remove(self)
            if not self.tournament.fixtures[-1]:
                self.tournament.fixtures[-1].append(
                    Game(self.tournament.BYE, self.tournament.BYE, self.tournament)
                )
            self.tournament.update_games()
        elif self.game_string == "":
            self.info(f"Undoing Game start")
            self.started = False
        elif self.protested != None:
            self.protested = None
        elif self.best_player:
            [i.undo_end() for i in self.teams]
            self.cards.clear()
            self.best_player = None
            self.primary_official.games_umpired -= 1
            self.primary_official.rounds_umpired -= self.rounds
            self.scorer.games_scored -= 1
            self.game_string = self.game_string[:-2]
            self.start(
                self.first_team_serves, self.teams[0].swapped, self.teams[1].swapped
            )
            self.load_from_string(self.game_string)
            logger.info(f"Undoing Game End... game string is now {self.game_string}")
        else:
            self.game_string = self.game_string[:-2]
            self.reload()
            self.info(f"Undoing... game string is now {self.game_string}")

    def reload(self):
        self._serve_clock = -1
        [i.end_timeout() for i in self.teams]
        self.cards.clear()
        self.start(self.first_team_serves, self.teams[0].swapped, self.teams[1].swapped)
        self.load_from_string(self.game_string)

    def as_map(self):
        dct = {
            "teamOne": {
                "name": self.teams[0].name,
                "score": self.teams[0].score,
                "players": [i.name for i in self.teams[0].start_players],
            },
            "teamTwo": {
                "name": self.teams[1].name,
                "score": self.teams[1].score,
                "players": [i.name for i in self.teams[1].start_players],
            },
            "court": self.court,
            "game": self.game_string,
            "started": self.started,
            "id": self.id,
            "firstTeamServed": self.first_team_serves,
            "official": self.primary_official.name
            if self.primary_official
            else "No one",
            "scorer": self.scorer.name if self.scorer else "No one",
            "startTime": self.start_time,
        }
        if self.best_player:  # game has been submitted and finalised
            dct["bestPlayer"] = self.best_player.name
            dct["cards"] = [i.reason for i in self.cards]
            dct["notes"] = self.notes
            dct["protested"] = self.protested
            dct["resolved"] = self.resolved
            dct["length"] = self.length
        return dct

    def display_map(self):
        dct = {
            "leftTeam": {
                "team": self.teams[0].name,
                "score": self.teams[0].score,
                "timeout": 30 - (time.time() - self.teams[0].time_out_time)
                if self.teams[0].time_out_time > 0
                else self.teams[0].timeouts - 1,
                "players": [i.name for i in self.teams[0].players],
                "captain": {
                    "name": self.teams[0].captain().name,
                    "green": self.teams[0].captain().green_carded,
                    "yellow": self.teams[0].captain().card_time_remaining > 0,
                    "receivedYellow": self.teams[0].captain().yellow_cards > 0,
                    "red": self.teams[0].captain().card_time_remaining < 0,
                    "serving": self.teams[0].captain().serving(),
                    "fault": self.teams[0].captain().serving()
                    and self.teams[0].faulted,
                    "cardPercent": self.teams[0].captain().card_time_remaining
                    / (self.teams[0].captain().card_duration or 1),
                },
                "notCaptain": {
                    "name": self.teams[0].not_captain().name,
                    "green": self.teams[0].not_captain().green_carded,
                    "yellow": self.teams[0].not_captain().card_time_remaining > 0,
                    "receivedYellow": self.teams[0].not_captain().yellow_cards > 0,
                    "red": self.teams[0].not_captain().card_time_remaining < 0,
                    "serving": self.teams[0].not_captain().serving(),
                    "fault": self.teams[0].not_captain().serving()
                    and self.teams[0].faulted,
                    "cardPercent": self.teams[0].not_captain().card_time_remaining
                    / (self.teams[0].not_captain().card_duration or 1),
                },
            },
            "rightTeam": {
                "team": self.teams[1].name,
                "score": self.teams[1].score,
                "timeout": 30 - (time.time() - self.teams[1].time_out_time)
                if self.teams[1].time_out_time > 0
                else self.teams[1].timeouts - 1,
                "players": [i.name for i in self.teams[1].players],
                "captain": {
                    "name": self.teams[1].captain().name,
                    "green": self.teams[1].captain().green_carded,
                    "yellow": self.teams[1].captain().card_time_remaining > 0,
                    "receivedYellow": self.teams[1].captain().yellow_cards > 0,
                    "red": self.teams[1].captain().card_time_remaining < 0,
                    "serving": self.teams[1].captain().serving(),
                    "fault": self.teams[1].captain().serving()
                    and self.teams[1].faulted,
                    "cardPercent": self.teams[1].captain().card_time_remaining
                    / (self.teams[1].captain().card_duration or 1),
                },
                "notCaptain": {
                    "name": self.teams[1].not_captain().name,
                    "green": self.teams[1].not_captain().green_carded,
                    "yellow": self.teams[1].not_captain().card_time_remaining > 0,
                    "receivedYellow": self.teams[1].not_captain().yellow_cards > 0,
                    "red": self.teams[1].not_captain().card_time_remaining < 0,
                    "serving": self.teams[1].not_captain().serving(),
                    "fault": self.teams[1].not_captain().serving()
                    and self.teams[1].faulted,
                    "cardPercent": self.teams[1].not_captain().card_time_remaining
                    / (self.teams[1].not_captain().card_duration or 1),
                },
            },
            "rounds": self.rounds,
            "umpire": self.primary_official.name,
            "court": self.court,
        }
        return dct

    def load_from_string(self, game_string: str):
        if self.bye:
            return
        j: str
        [i.reset() for i in self.teams]
        self.rounds = 0
        self.teams[not self.first_team_serves].serving = True
        for j in chunks_sized(game_string, 2):
            team = self.teams[not j[1].isupper()]
            first = j[1].upper() == "L"
            c = j[0].lower()
            if c == "s":
                team.score_point(first)
            elif c == "a":
                team.score_point(None, True)
            elif c == "g":
                team.green_card(first)
            elif c == "y":
                team.yellow_card(first)
            elif c == "v":
                team.red_card(first)
            elif c == "f":
                team.fault()
            elif c == "t":
                team.timeout()
                team.end_timeout()
            elif c == "x":
                team.sub_player(first)
            elif c == "e":
                team.forfeit()
            elif c == "!":
                c2 = j[1].lower()
                if c2 == "h":
                    self.swap_serve()
                elif c2 == "u":
                    team.swap_players(True)
                elif c2 == "w":
                    self.swap_serve_team()
            elif c.isdigit():
                if int(c) <= 3:
                    team.yellow_card(first, int(c) + 10)
                else:
                    team.yellow_card(first, int(c))
        self.game_string = game_string

    def fixture_to_table_row(self):
        return [self.teams[0], self.teams[1], self.score_string, self.id]

    def __repr__(self):
        return f"{self.teams[0].short_name} vs {self.teams[1].short_name}"

    def info(self, message):
        if self.id < 0:
            return
        logger.info(f"(Game {self.id}) {message}")

    def protest(self, first_team, second_team):
        self.protested = first_team + 2 * second_team

    def resolve(self):
        self.resolved = True

    def get_stats(self):
        serve_streak = []
        ace_streak = []
        for i in self.playing_players:
            serve_streak += i.serve_streak
            ace_streak += i.ace_streak
        return {
            "Rounds": self.rounds,
            "Score Difference": abs(self.teams[0].score - self.teams[1].score),
            "Elo Gap": abs(self.teams[0].elo_at_start - self.teams[1].elo_at_start),
            "Length": self.length,
            "Cards": len(self.cards),
            "Green Cards": len([i for i in self.cards if i.color == "Green"]),
            "Yellow Cards": len([i for i in self.cards if i.color == "Yellow"]),
            "Red Cards": len([i for i in self.cards if i.color == "Red"]),
            "Timeouts Used": sum(i.timeouts for i in self.teams),
            "Aces": sum(sum(j.aces_scored for j in i.players) for i in self.teams),
            "Ace Percentage": sum(
                sum(j.aces_scored for j in i.players) for i in self.teams
            )
            / self.rounds,
            "Faults": sum(sum(j.faults for j in i.players) for i in self.teams),
            "Faults Percentage": sum(
                sum(j.faults for j in i.players) for i in self.teams
            )
            / self.rounds,
            "Max Serving Streak": max(serve_streak),
            "Avg Serving Streak": sum(serve_streak) / len(serve_streak),
            "Max Ace Streak": max(ace_streak),
            "Avg Ace Streak": sum(ace_streak) / len(ace_streak),
        }
