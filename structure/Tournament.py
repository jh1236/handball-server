import json
from typing import Generator, Type

from structure.Game import Game
from structure.OfficiatingBody import Officials
from structure.Player import Player
from structure.Team import Team
from tournaments.FixtureMaker import FixtureMaker, get_type_from_name
from utils.logging_handler import logger


class Tournament:
    def __init__(self, file: str, fixtures: Type[FixtureMaker],
                 finals: Type[FixtureMaker]):
        # TODO: move this to the constructor
        self.filename = f"./resources/tournaments/{file}"
        self.in_finals: bool = False
        self.teams = []
        self.fixtures: list[list[Game]] = []
        self.finals: list[list[Game]] = []
        self.fixtures_class = None
        self.finals_class = None
        self.initial_load()
        self.fixtures_gen: Generator[list[Game]] = None
        self.finals_gen: Generator[list[Game]] = None
        self.officials: Officials = Officials(self)
        self.load()

    def games_to_list(self) -> list[Game]:
        return [game for r in self.fixtures for game in r] + [game for r in self.finals for game in r]

    def ladder(self):
        return sorted(self.teams, key=lambda a: (-a.games_won, -(a.get_stats()["Point Difference"])))

    def update_games(self):
        if not self.in_finals:
            if not self.fixtures or all([i.best_player for i in self.fixtures[-1]]):
                try:
                    self.fixtures.append(next(self.fixtures_gen))
                except StopIteration:
                    logger.info("Entering Finals!")
                    self.in_finals = True
                    self.finals.append(next(self.finals_gen))
        elif all([i.best_player for i in self.finals[-1]]):
            try:
                logger.info("Next round of finals")
                self.finals.append(next(self.finals_gen))
                logger.info(self.finals[-1])
            except StopIteration:
                logger.info("Last Game has been added")
        self.appoint_umpires()
        self.assign_rounds()
        self.assign_ids()

    def get_game(self, game_id: int) -> Game:
        self.update_games()
        if game_id >= len(self.games_to_list()):
            raise ValueError(f"Game index {game_id} out of bounds.")
        return self.games_to_list()[game_id]

    def assign_ids(self):
        for i, g in enumerate(self.games_to_list()):
            g.id = i

    def appoint_umpires(self):
        for prev, game, next in zip([None] + self.games_to_list()[:-1], self.games_to_list(),
                                    self.games_to_list()[1:] + [None]):
            if game.bye: continue
            if game.primary_official is not None: continue
            teams = [i.team for i in game.teams] + ([] if not next else [i.team for i in next.teams])
            for p in self.officials.get_primary_officials():
                if prev and prev.primary_official == p: continue
                if p.team and p.team in teams: continue
                game.set_primary_official(p)
                break

    def assign_rounds(self):
        for i, r in enumerate(self.fixtures):
            for j in r:
                j.round_number = i

    def save(self):
        logger.info("Saving...")
        d = {
            "details": {
                "fixture_generator": self.fixtures_class.get_name(),
                "finals_generator": self.finals_class.get_name(),
            },
            "games": [[j.as_map() for j in i if j.started] for i in self.fixtures],
            "finals": [[j.as_map() for j in i if j.started] for i in self.finals],
            "teams": {i.name: [j.name for j in i.players] for i in self.teams}
        }
        with open(self.filename, "w+") as fp:
            json.dump(d, fp, indent=4, sort_keys=True)

    def dump(self):
        self.fixtures = []
        self.finals = []
        self.save()
        self.load()
        print(self.fixtures)

    def load(self):
        [i.reset() for i in self.teams]
        self.fixtures_gen: Generator[list[Game]] = self.fixtures_class.get_generator()
        self.finals_gen: Generator[list[Game]] = self.finals_class.get_generator()
        self.fixtures = []
        self.in_finals = False
        with open(f"{self.filename}", "r+") as fp:
            data = json.load(fp)
        self.update_games()  # used to initialise the first round
        for i, r in enumerate([[Game.from_map(j, self) for j in i] for i in data.get("games", [])]):
            for j, g in enumerate(r):
                self.fixtures[i][j] = g
                self.update_games()
        for i, r in enumerate([[Game.from_map(j, self) for j in i] for i in data.get("finals", [])]):
            for j, g in enumerate(r):
                self.finals[i][j] = g
                self.update_games()
        self.assign_ids()
        self.assign_rounds()
        self.appoint_umpires()
        self.update_games()

    def initial_load(self):
        self.teams = []
        with open(f"{self.filename}", "r+") as fp:
            data = json.load(fp)
            self.teams = [Team(k, [Player(i) for i in v]) for k, v in data["details"]["teams"].items()]
            for i in self.teams:
                i.tournament = self
                for j in i.players:
                    j.tournament = self
            self.fixtures_class = get_type_from_name(data["details"]["fixtures_generator"])(self)
            self.finals_class = get_type_from_name(data["details"]["finals_generator"])(self)
