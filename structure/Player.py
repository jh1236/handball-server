from typing import Any


class Player:
    def __init__(self, name: str):
        self._team = None
        self.tournament = None
        self.name: str = name
        self.faults: int = 0
        self.double_faults: int = 0
        self.points_scored: int = 0
        self.aces_scored: int = 0
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.votes: int = 0
        self.red_cards: int = 0
        self.time_on_court: int = 0
        self.time_carded: int = 0
        self.rounds_played: int = 0
        self.rounds_carded: int = 0
        self.points_served: int = 0
        self.played: int = 0
        self.wins: int = 0

    @property
    def biggest_card(self):
        if self.red_cards > 0:
            return "red"
        elif self.yellow_cards > 0:
            return "yellow"
        elif self.green_cards > 0:
            return "green"
        return None

    @property
    def biggest_card_hex(self):
        if self.red_cards > 0:
            return "#EC4A4A"
        elif self.yellow_cards > 0:
            return "#FCCE6E"
        elif self.green_cards > 0:
            return "#84AA63"
        return "#FFFFFF"

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
        total = 0
        game_teams: list[GamePlayer] = []
        for i in self.tournament.games_to_list():
            player_names = [j.name for j in i.players()]
            if i.in_progress() and self.name in player_names:
                game_teams.append(i.players()[player_names.index(self.name)])
        total += self.green_cards + sum([i.green_cards for i in game_teams])
        total += self.yellow_cards + sum([i.yellow_cards for i in game_teams])
        total += self.red_cards + sum([i.red_cards for i in game_teams])
        return total

    def get_stats(self):
        game_teams: list[GamePlayer] = []
        if self.tournament:
            for i in self.tournament.games_to_list():
                player_names = [j.name for j in i.players()]
                if i.in_progress() and self.name in player_names:
                    game_teams.append(i.players()[player_names.index(self.name)])

        points_scored = self.points_scored + sum([i.points_scored for i in game_teams])
        aces_scored = self.aces_scored + sum([i.aces_scored for i in game_teams])
        green_cards = self.green_cards + sum([i.green_cards for i in game_teams])
        yellow_cards = self.yellow_cards + sum([i.yellow_cards for i in game_teams])
        red_cards = self.red_cards + sum([i.red_cards for i in game_teams])
        time_on_court = self.time_on_court + sum([i.time_on_court for i in game_teams])
        time_carded = self.time_carded + sum([i.time_carded for i in game_teams])
        faults = self.faults + sum([i.faults for i in game_teams])
        double_faults = self.double_faults + sum([i.double_faults for i in game_teams])
        played = self.played + len(game_teams)
        return {
            "B&F Votes": self.votes,
            "Points scored": points_scored,
            "Aces scored": aces_scored,
            "Faults": faults,
            "Double Faults": double_faults,
            "Green Cards": green_cards,
            "Yellow Cards": yellow_cards,
            "Red Cards": red_cards,
            "Rounds on Court": time_on_court,
            "Rounds Carded": time_carded,
            "Games Played": played,
            "Games Won": self.wins,
        }

    def get_stats_detailed(self):
        game_teams: list[GamePlayer] = []
        if self.tournament:
            for i in self.tournament.games_to_list():
                player_names = [j.name for j in i.players()]
                if i.in_progress() and self.name in player_names:
                    game_teams.append(i.players()[player_names.index(self.name)])

        served = self.points_served + sum([i.points_served for i in game_teams])
        d = self.get_stats()
        d = d | {
            "Points served": served,
            "Points Per Game": round(d["Points scored"] / (d["Games Played"] or 1), 2),
            "Aces Per Game": round(d["Aces scored"] / (d["Games Played"] or 1), 2),
            "Cards Per Game": round(
                (d["Green Cards"] + d["Yellow Cards"] + d["Red Cards"])
                / (d["Games Played"] or 1),
                2,
            ),
            "Percentage Aces": f'{round(d["Aces scored"] / (served or 1), 2) * 100: .1f}%',
            "Percentage of Points scored": f"{round(d['Points scored'] / (d['Rounds on Court'] or 1), 2) * 100: .1f}%",
        }
        return d

    def add_stats(self, d: dict[str, Any]):
        self.votes += d.get("B&F Votes", 0)
        self.points_scored += d.get("Points scored", 0)
        self.aces_scored += d.get("Aces scored", 0)
        self.faults += d.get("Faults", 0)
        self.double_faults += d.get("Double Faults", 0)
        self.green_cards += d.get("Green Cards", 0)
        self.yellow_cards += d.get("Yellow Cards", 0)
        self.red_cards += d.get("Red Cards", 0)
        self.time_on_court += d.get("Rounds on Court", 0)
        self.time_carded += d.get("Rounds Carded", 0)
        self.played += d.get("Games Played", 0)
        self.wins += d.get("Games Won", 0)
        self.points_served += d.get("Points served", 0)

    def nice_name(self):
        return self.name.lower().replace(" ", "_")

    def game_player(self, game, captain):
        return GamePlayer(self, game, captain)

    def reset(self):
        self.faults = 0
        self.double_faults = 0
        self.points_scored = 0
        self.aces_scored = 0
        self.green_cards = 0
        self.yellow_cards = 0
        self.votes = 0
        self.red_cards = 0
        self.time_on_court = 0
        self.time_carded = 0
        self.rounds_played = 0
        self.rounds_carded = 0

    def set_tournament(self, tournament):
        self.tournament = tournament
        return self


class GamePlayer:
    def __init__(self, player: Player, game, captain):
        self.points_served: int = 0
        self.game = game
        self.double_faults: int = 0
        self.player: Player = player
        self.name: str = self.player.name
        self.faults: int = 0
        self.points_scored: int = 0
        self.aces_scored: int = 0
        self.time_on_court: int = 0
        self.captain = captain
        self.time_carded: int = 0
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.card_time_remaining: int = (
            0  # how many rounds the player is carded for (-1 is infinite)
        )
        self.card_duration: int = (
            0  # total time the player is carded for (used for progress bar in app)
        )
        self.green_carded: bool = False
        self.best: bool = False

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

    def green_card(self):
        self.green_carded = True
        self.green_cards += 1

    def yellow_card(self, time):
        self.yellow_cards += 1
        if self.card_time_remaining >= 0:
            self.card_time_remaining += time
            self.card_duration += time

    def red_card(self):
        self.red_cards += 1
        self.card_time_remaining = -1

    def is_carded(self):
        return self.card_time_remaining != 0

    def next_point(self):
        if self.is_carded():
            self.time_carded += 1
        else:
            self.time_on_court += 1
        if self.card_time_remaining > 0:
            self.card_time_remaining -= 1

    def reset(self):
        self.card_time_remaining = 0
        self.points_served = 0
        self.card_duration = 0
        self.points_scored = 0
        self.aces_scored = 0
        self.time_on_court = 0
        self.faults = 0
        self.double_faults = 0
        self.time_carded = 0
        self.green_cards = 0
        self.yellow_cards = 0
        self.red_cards = 0
        self.green_carded = False

    def end(self, won, final=False):
        if final:
            return
        self.player.points_scored += self.points_scored
        self.player.points_served += self.points_served
        self.player.aces_scored += self.aces_scored
        self.player.time_on_court += self.time_on_court
        self.player.time_carded += self.time_carded
        self.player.green_cards += self.green_cards
        self.player.yellow_cards += self.yellow_cards
        self.player.red_cards += self.red_cards
        self.player.faults += self.faults
        self.player.double_faults += self.double_faults
        self.player.votes += self.best
        self.player.played += 1
        self.player.wins += won

    def undo_end(self, won):
        self.player.points_scored -= self.points_scored
        self.player.points_served -= self.points_served
        self.player.aces_scored -= self.aces_scored
        self.player.time_on_court -= self.time_on_court
        self.player.time_carded -= self.time_carded
        self.player.green_cards -= self.green_cards
        self.player.yellow_cards -= self.yellow_cards
        self.player.red_cards -= self.red_cards
        self.player.faults -= self.faults
        self.player.double_faults -= self.double_faults
        self.player.votes -= self.best
        self.player.played -= 1
        self.player.wins -= won

    def tidy_name(self):
        if not " " in self.name:
            return self.name
        first, second = self.name.split(" ", 1)
        second = " " + second[0] + "."
        return first + second

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

    def serve(self):
        self.points_served += 1

    def fault(self):
        self.faults += 1

    def double_fault(self):
        self.double_faults += 1

    def __repr__(self):
        return self.name

    def serving(self):
        return self.game.server() and self.game.server().nice_name() == self.nice_name()
