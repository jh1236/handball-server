import json
from typing import Generator

from structure.Game import Game
from utils.logging_handler import logger


class Fixtures:
    def __init__(self, tournament, fixtures: Generator[list[Game], None, None],
                 finals: Generator[list[Game], None, None]):
        # TODO: move this to the constructor
        file = "games.json"
        self.filename = f"./resources/tournaments/{file}"
        self.in_finals: bool = False
        self.tournament = tournament
        self.fixtures_gen: Generator[list[Game]] = fixtures
        self.finals_gen: Generator[list[Game]] = finals
        self.fixtures: list[list[Game]] = []
        self.finals: list[list[Game]] = []

    def games_to_list(self) -> list[Game]:
        return [game for r in self.fixtures for game in r] + [game for r in self.finals for game in r]

    def ladder(self):
        return sorted(self.tournament.teams, key=lambda a: (-a.games_won, -(a.get_stats()["Point Difference"])))

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
            if game.primary_official is not None: continue
            teams = [i.team for i in game.teams] + ([] if not next else [i.team for i in next.teams])
            for p in self.tournament.officials.get_primary_officials():
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
            "games": [[j.as_map() for j in i if j.started] for i in self.fixtures],
            "finals": [[j.as_map() for j in i if j.started] for i in self.finals]
        }
        with open(self.filename, "w+") as fp:
            json.dump(d, fp, indent=4, sort_keys=True)

    def load(self):
        self.fixtures = []
        self.update_games()  # used to initialise the first round
        with open(f"{self.filename}", "r+") as fp:
            data = json.load(fp)
        self.in_finals = False
        for i, r in enumerate([[Game.from_map(j, self.tournament) for j in i] for i in data.get("games", [])]):
            for j, g in enumerate(r):
                self.fixtures[i][j] = g
                self.update_games()
        for i, r in enumerate([[Game.from_map(j, self.tournament) for j in i] for i in data.get("finals", [])]):
            for j, g in enumerate(r):
                self.finals[i][j] = g
                self.update_games()
        self.assign_ids()
        self.assign_rounds()
        self.appoint_umpires()
        self.update_games()
