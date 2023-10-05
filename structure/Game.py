import typing

from structure.Player import GamePlayer
from utils.util import chunks_sized
from utils.logging_handler import logger

if typing.TYPE_CHECKING:
    from structure.Team import GameTeam


class Game:
    record_stats = True

    @classmethod
    def from_map(cls, game_map, tournament):
        team_one = [i for i in tournament.teams if i.name == game_map["teamOne"]["name"]][0]
        team_two = [i for i in tournament.teams if i.name == game_map["teamTwo"]["name"]][0]
        swapped = game_map["firstTeamServed"]
        game = Game(team_one, team_two, tournament)
        team_one_swap = team_one.players[0].name != game_map["teamOne"]["players"][0]
        team_two_swap = team_two.players[0].name != game_map["teamTwo"]["players"][0]
        game.set_primary_official(
            [i for i in tournament.officials.get_primary_officials() if i.name == game_map["official"]][0])
        if not game_map["started"]: return game
        game.start(swapped, team_one_swap, team_two_swap)
        game.load_from_string(game_map["game"])
        if game_map.get("bestPlayer", False):
            game.end(game_map["bestPlayer"])

        Game.record_stats = True
        return game

    def __init__(self, team_one, team_two, tournament, final: bool = False):
        self.tournament = tournament
        self.id: int = -1
        self.game_string: str = ""
        self.rounds: int = 0
        self.started: bool = False
        self.best_player: GamePlayer | None = None
        self.teams: list[GameTeam] = [team_one.get_game_team(self), team_two.get_game_team(self)]
        self.is_final = final
        if not final and self.teams[0].team.first_ratio() > self.teams[1].team.first_ratio():
            self.teams.reverse()
        self.first_team_serves: bool = False
        self.primary_official = None
        self.round_number: int = 0

    def set_primary_official(self, o):
        o.games_officiated += 1
        self.primary_official = o

    def add_to_game_string(self, string: str, team):
        if team == self.teams[0]:
            self.game_string += string.upper()
        else:
            self.game_string += string.lower()

    def next_point(self):
        self.rounds += 1
        [i.next_point() for i in self.teams]

    def team_serving(self):
        return [i for i in self.teams if i.serving][0]

    def server(self):
        serving_team = self.team_serving()
        server = serving_team.players[not serving_team.first_player_serves]
        if server.is_carded():
            server = serving_team.players[serving_team.first_player_serves]
        return server

    def players(self) -> list[GamePlayer]:
        return [*self.teams[0].players, *self.teams[1].players]

    def winner(self):
        return max(self.teams, key=lambda a: a.score).team

    def loser(self):
        return min(self.teams, key=lambda a: a.score).team

    def print_gamestate(self):
        logger.info(f"         {self.teams[0].__repr__():^15}| {self.teams[1].__repr__():^15}")
        logger.info(f"score   :{self.teams[0].score:^15}| {self.teams[1].score:^15}")
        logger.info(f"cards   :{self.teams[0].card_time():^15}| {self.teams[1].card_time():^15}")
        logger.info(f"timeouts:{self.teams[0].timeouts:^15}| {self.teams[1].timeouts:^15}")

    def start(self, team_one_serves, swap_team_one, swap_team_two):
        self.started = True
        self.teams[0].start(team_one_serves, swap_team_one)
        self.teams[1].start(not team_one_serves, swap_team_two)
        self.first_team_serves = team_one_serves
        self.info(f"Started, {self.server().nice_name()} serving from team {self.team_serving().nice_name()}")

    def end(self, best_player: str):
        if self.game_ended():
            if self.best_player:
                [i.undo_end() for i in self.teams]
                self.primary_official.games_umpired -= 1
                self.primary_official.rounds_umpired -= self.rounds
            self.teams[0].team.listed_first += 1
            self.best_player = []
            for i in self.players():
                if i.name == best_player:
                    self.best_player = i
                    i.best_player()
                    break
            [i.end(self.is_final) for i in self.teams]
            self.primary_official.games_umpired += 1
            self.primary_official.rounds_umpired += self.rounds
            self.info(
                f"game {self.id} is over! Winner was {self.winner().nice_name()}, Best Player is {self.best_player.nice_name()}")
            self.tournament.fixtures.update_games()

    def in_progress(self):
        return self.started and not self.best_player

    def game_ended(self):
        return max([i.score for i in self.teams]) >= 11 and abs(self.teams[0].score - self.teams[1].score) >= 2

    def undo(self):
        if self.game_string == "":
            self.info(f"Undoing Game start")
            self.started = False
        elif self.best_player:
            [i.undo_end() for i in self.teams]
            self.best_player = None
            self.primary_official.games_umpired -= 1
            self.primary_official.rounds_umpired -= self.rounds
            self.game_string = self.game_string[:-2]
            self.load_from_string(self.game_string)
            logger.info(f"Undoing Game End... game string is now {self.game_string}")
        else:
            self.game_string = self.game_string[:-2]
            self.load_from_string(self.game_string)
            self.info(f"Undoing... game string is now {self.game_string}")

    def as_map(self):
        dct = {
            "teamOne": {
                "name": self.teams[0].name,
                "score": self.teams[0].score,
                "players": [i.name for i in self.teams[0].players]
            },
            "teamTwo": {
                "name": self.teams[1].name,
                "score": self.teams[1].score,
                "players": [i.name for i in self.teams[1].players]
            },
            "game": self.game_string,
            "started": self.started,
            "id": self.id,
            "firstTeamServed": self.first_team_serves,
            "official": self.primary_official.name
        }
        if self.best_player:  # game has been submitted and finalised
            dct["bestPlayer"] = self.best_player.name
        return dct

    def display_map(self):
        serving_team = [*[i for i in self.teams if i.serving]]
        if serving_team:
            serving_team = serving_team[0]
            server = serving_team.players[not serving_team.first_player_serves]
            if server.is_carded():
                server = serving_team.players[serving_team.first_player_serves].name
            else:
                server = server.name
        else:
            server = "None"
        dct = {
            "server": server,
            "teamOne": {
                "name": self.teams[0].name,
                "players": [i.name for i in self.teams[0].players],
                "score": self.teams[0].score,
                "cards": self.teams[0].card_time(),
                "greenCard": self.teams[0].green_carded,
                "cardDuration": self.teams[0].card_duration(),
            },
            "teamTwo": {
                "name": self.teams[1].name,
                "players": [i.name for i in self.teams[1].players],
                "score": self.teams[1].score,
                "cards": self.teams[1].card_time(),
                "greenCard": self.teams[1].green_carded,
                "cardDuration": self.teams[1].card_duration(),
            },
            "firstTeamServing": self.teams[0].serving,
            "game": self.game_string,
            "started": self.started,
            "rounds": self.rounds,
        }
        return dct

    def load_from_string(self, game_string: str):
        j: str
        [i.reset() for i in self.teams]
        self.rounds = 0
        self.teams[not self.first_team_serves].serving = True
        for j in chunks_sized(game_string, 2):
            team = self.teams[not j[1].isupper()]
            first = j[1].upper() == 'L'
            c = j[0].lower()
            if c == 's':
                team.score_point(first)
            elif c == 'a':
                team.score_point(first, True)
            elif c == 'g':
                team.green_card(first)
            elif c == 'y':
                team.yellow_card(first)
            elif c == 'v':
                team.red_card(first)
            elif c == 'f':
                team.fault()
            elif c == 't':
                team.timeout()
            elif c.isdigit():
                if c == '0':
                    team.yellow_card(first, 10)
                else:
                    team.yellow_card(first, int(c))
        self.game_string = game_string

    def fixture_to_table_row(self):
        return [self.teams[0], self.teams[1], self.score_string(), self.id]

    def __repr__(self):
        return f"{self.teams[0]} vs {self.teams[1]}"

    def score_string(self):
        return f"{self.teams[0].score} - {self.teams[1].score}"

    def info(self, message):
        if self.id < 0:
            return
        logger.info(f"(Game {self.id}) {message}")
