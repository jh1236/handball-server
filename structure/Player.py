import datetime
from typing import Any

from structure.Card import Card
from utils.statistics import initial_elo, get_player_stats

elo_map = {}


class Player:
    def __init__(self, name: str):
        self._team = None
        self.tournament = None
        self.name: str = name
        if self.nice_name() not in elo_map:
            elo_map[self.nice_name()] = initial_elo

        self.cards: list[Card] = []

    @property
    def elo(self):
        return elo_map[self.nice_name()]

    def change_elo(self, delta: int, game):
        elo_map[self.nice_name()] += delta

    @property
    def team(self):
        if self._team is not None:
            return self._team
        return sorted(
            [
                i
                for i in self.tournament.teams
                if self.nice_name() in [j.nice_name() for j in i.players]
            ],
            key=lambda a: not a.has_photo,
        )[0]

    def __repr__(self):
        return self.name

    def total_cards(self):
        return self.get_stats_detailed()["Cards"]

    def get_stats(self):
        return get_player_stats(self.tournament, self, 0)

    def get_stats_detailed(self):
        return get_player_stats(self.tournament, self, 1)

    def nice_name(self):
        return self.name.lower().replace(" ", "_").replace("'", "")

    def game_player(self, game, team, captain):
        return GamePlayer(self, game, team, captain)

    def set_tournament(self, tournament):
        self.tournament = tournament
        return self


class GamePlayer:
    def __init__(self, player: Player, game, team, captain):
        
        self.team = team
        self.game = game
        self.player: Player = player
        self.name: str = self.player.name
        self._tidy_name = None

        self._card_time_remaining = 0
        self._card_duration = 0
        self.cards: list[Card] = []
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.green_carded: bool = False

        self.elo_delta = None
        self.elo_at_start: float = self.player.elo

        self.won_while_serving = 0
        self.points_served: int = 0
        self.ace_streak: list[int] = [0]
        self.serve_streak: list[int] = [0]
        self.serves_received: int = 0
        self.serve_return: int = 0
        self.double_faults: int = 0
        self.faults: int = 0
        self.aces_scored: int = 0

        self.time_carded: int = 0
        self.points_scored: int = 0
        self.time_on_court: int = 0
        self.captain = captain
        self.best: bool = False
        self.subbed_off: bool = False
        self.started_sub: bool = False
        self.subbed_on: bool = False

    @property
    def elo_delta_string(self):
        from website.website import sign

        return f"{round(self.elo_at_start, 2)}" + (
            f"  [{sign(self.elo_delta)}{round(abs(self.elo_delta), 2)}]"
            if self.elo_delta
            else "  [+0]"
        )

    @property
    def card_time_remaining(self):
        if "null" in self.nice_name():
            return -1
        return self._card_time_remaining

    @property
    def card_duration(self):
        if "null" in self.nice_name():
            return 1
        return self._card_duration

    def biggest_card_hex(self):
        if self.red_cards > 0:
            return "#EC4A4A"
        elif self.yellow_cards > 0:
            return "#FCCE6E"
        elif self.green_cards > 0:
            return "#84AA63"
        return "#FFFFFF"

    def score_point(self, ace: bool):
        if ace:
            self.aces_scored += 1
        self.points_scored += 1

    def best_player(self):
        self.best = True

    def nice_name(self):
        return self.player.nice_name()

    def first_name(self):
        if " " not in self.name:
            return self.name
        first, second = self.name.split(" ", 1)
        others = self.game.current_players
        for i in others:
            if i.name == self.name or " " not in i.name:
                continue
            other_first = i.name.split(" ", 1)[0]
            if other_first == first:
                return self.name
        return first

    def green_card(self):
        self.green_carded = True
        self.green_cards += 1
        card = Card(self, 0)
        self.cards.append(card)
        self.game.cards.append(card)

    def yellow_card(self, time):
        self.yellow_cards += 1
        if self.card_time_remaining >= 0:
            self._card_time_remaining += time
            self._card_duration = self.card_time_remaining
        card = Card(self, time)
        self.cards.append(card)
        self.game.cards.append(card)

    def red_card(self):
        self.red_cards += 1
        self._card_time_remaining = -1
        card = Card(self, -1)
        self.cards.append(card)
        self.game.cards.append(card)

    def is_carded(self):
        return "null" in self.nice_name() or self.card_time_remaining != 0

    def next_point(self):
        if self.is_carded():
            self.time_carded += 1
        else:
            self.time_on_court += 1
        if self.card_time_remaining > 0:
            self._card_time_remaining -= 1

    def reset(self):
        self._card_time_remaining = 0
        self.won_while_serving = 0
        self.points_served = 0
        self._card_duration = 0
        self.points_scored = 0
        self.aces_scored = 0
        self.time_on_court = 0
        self.faults = 0
        self.double_faults = 0
        self.time_carded = 0
        self.serve_return = 0
        self.serve_streak: list[int] = [0]
        self.ace_streak: list[int] = [0]
        self.serves_received: int = 0
        self.serve_return: int = 0
        self.subbed_on = False
        self.subbed_off = False
        self.green_cards = 0
        self.yellow_cards = 0
        self.red_cards = 0
        self.green_carded = False

    def end(self, won, final=False):
        if final or self.time_carded + self.time_on_court == 0:
            return
        self.player.cards += self.cards

    def undo_end(self, won):
        if self.time_carded + self.time_on_court == 0 or not self.game.ranked:
            return
        for i in self.cards:
            self.player.cards.remove(i)

    def tidy_name(self):
        if self._tidy_name is not None:
            return self._tidy_name
        if " " not in self.name:
            self._tidy_name = self.name
            return self.name
        first, second = self.name.split(" ", 1)
        others = self.game.tournament_id.players
        for i in others:
            if i.name == self.name:
                continue
            if " " not in i.name:
                continue
            other_first, other_second = i.name.split(" ", 1)
            if other_first[0] == first[0] and second == other_second:
                first = first[:2] + ". "
                self._tidy_name = first + second
                return self._tidy_name
        first = first[0] + ". "
        self._tidy_name = first + second
        return self._tidy_name

    def get_stats(self):
        return {
            "Points Scored": self.points_scored,
            "Aces": self.aces_scored,
            "Faults": self.faults,
            "Double Faults": self.double_faults,
            "Rounds Played": self.time_on_court,
            "Rounds On Bench": self.time_carded,
            "Green Cards": self.green_cards,
            "Yellow Cards": self.yellow_cards,
            "Red Cards": self.red_cards,
        }

    def get_stats_detailed(self):
        from start import comps

        games_total = 0
        for i in comps.values():
            if i.details["sort"] < self.game.tournament_id.details["sort"]:
                for j in i.games_to_list():
                    if j.ranked and self.nice_name() in [
                        k.nice_name() for k in j.playing_players
                    ]:
                        games_total += 1
        for i in self.game.tournament_id.games_to_list():
            if i.id >= self.game.id:
                break
            if i.ranked and self.nice_name() in [
                k.nice_name() for k in i.playing_players
            ]:
                games_total += 1
        return {
            "Elo Delta": self.elo_delta if self.elo_delta else 0,
            "Elo": self.elo_at_start + (self.elo_delta if self.elo_delta else 0),
            "Team Elo Difference": self.team.elo_at_start
            - self.team.opponent.elo_at_start,
            "Teammate Elo Difference": 0
            if len(self.team.all_players) == 1
            else self.elo_at_start
            - (self.team.elo_at_start * len(self.team.all_players) - self.elo_at_start)
            / (len(self.team.all_players) - 1),
            "Solo Elo Difference": self.elo_at_start - self.team.opponent.elo_at_start,
            "Points Scored": self.points_scored,
            "Points Served": self.points_served,
            "Timeline": games_total,
            "Time Taken": "?:??" if self.game.length < 0 else str(datetime.timedelta(seconds=self.game.length)),
            "Seconds Elapsed": self.game.length,
            "Aces Scored": self.aces_scored,
            "Max Ace Streak": max(self.ace_streak),
            "Max Serving Streak": max(self.serve_streak),
            "Serves Received": self.serves_received,
            "Serves Returned": self.serve_return,
            "Serves Missed": self.serves_received - self.serve_return,
            "Percentage of Points Scored": 100
            * self.points_scored
            / (self.game.rounds or 1),
            "Percentage of Points Scored for Team": 100
            * self.points_scored
            / (self.team.score or 1),
            "Return Rate": 100 * self.serve_return / (self.serves_received or 1),
            "Ace Rate": 100 * self.aces_scored / (self.points_served or 1),
            "Faults": self.faults,
            "Double Faults": self.double_faults,
            "Rounds Played": self.time_on_court,
            "Rounds Carded": self.time_carded,
            "Rounds": self.game.rounds,
            "Green Cards": self.green_cards,
            "Yellow Cards": self.yellow_cards,
            "Red Cards": self.red_cards,
            "Score Difference": (self.team.score - self.team.opponent.score)
            if self.team.opponent
            else 0,
            "Cards": self.red_cards + self.yellow_cards + self.green_cards,
            "Result": int(self.game.winner.nice_name() == self.team.nice_name())\
        }

    def get_game_details(self):
        from start import comps

        games_total = 0
        for i in comps.values():
            if i.details["sort"] < self.game.tournament_id.details["sort"]:
                for j in i.games_to_list():
                    if j.ranked and self.nice_name() in [
                        k.nice_name() for k in j.playing_players
                    ]:
                        games_total += 1
        for i in self.game.tournament_id.games_to_list():
            if i.id >= self.game.id:
                break
            if i.ranked and self.nice_name() in [
                k.nice_name() for k in i.playing_players
            ]:
                games_total += 1
        return {
            "Points Scored": self.points_scored,
            "Aces Scored": self.aces_scored,
            "Faults": self.faults,
            "Double Faults": self.double_faults,
            "Green Cards": self.green_cards,
            "Yellow Cards": self.yellow_cards,
            "Red Cards": self.red_cards,
            "Rounds Played": self.time_on_court,
            "Rounds Carded": self.time_carded,
            "Result": "Won"
            if self.game.winner.nice_name() == self.team.nice_name()
            else "Lost",
            "Cards": self.red_cards + self.yellow_cards + self.green_cards,
            "Points Served": self.points_served,
            "Max Serving Streak": max(self.serve_streak),
            "Max Ace Streak": max(self.ace_streak),
            "Serves Received": self.serves_received,
            "Serves Returned": self.serve_return,
            "Serves Missed": self.serves_received - self.serve_return,
            "Court": self.game.court + 1,
            "Side": "Left"
            if self.team.players[0].nice_name() == self.nice_name()
            else "Right",
            "Format": "Championship"
            if "championship" in self.game.tournament_id.nice_name()
            else "Practice",
            "Team Size": len(self.team.playing_players),
            "Round": self.game.round_number,
            "Rounds": self.game.rounds,
            "Forfeit": self.game.is_forfeited
            and self.game.winner.nice_name() != self.team.nice_name(),
            "Finals": self.game.is_final,
            "Best on Ground": self.game.best_player.nice_name() == self.nice_name(),
            "Made Finals": any(
                [
                    self.team.nice_name() in [k.nice_name() for k in i.teams]
                    for i in self.game.tournament_id.finals_to_list()
                ]
            ),
            "Ranked": self.game.ranked,
            "Umpire": self.game.primary_official.name,
            "Scorer": self.game.scorer.name,
            "Served First": self.game.teams[not self.game.first_team_serves].nice_name()
            == self.team.nice_name(),
            "Tournament": self.game.tournament_id.name,
            "Team": self.team.name,
            "Player": self.name,
        }

    def fault(self):
        self.faults += 1

    def double_fault(self):
        self.double_faults += 1

    def __repr__(self):
        return self.name

    def serving(self):
        return self.game.server and self.game.server.nice_name() == self.nice_name()

    def change_elo(self, delta, game):
        """
        delta: float    - the raw elo delta calculated by the elo function (https://www.desmos.com/calculator/3grcevz6t7)
        game: Game      - The game that this change is caused by
        """
        self.elo_delta = delta
        self.player.change_elo(self.elo_delta, game)


ff = Player("Forfeit")


def forfeit_player(game):
    return ff.game_player(game, None, False)
