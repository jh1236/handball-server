import json
import os
from typing import Generator, Any

from FixtureMakers.FixtureMaker import get_type_from_name
from structure.Game import Game
from structure.OfficiatingBody import Official, get_officials, NoOfficial
from structure.Player import Player
from structure.Team import Team, BYE
from utils.logging_handler import logger


class Tournament:
    def __init__(self, file: str):
        if file != "-":
            self.filename = f"./config/tournaments/{file}"
        else:
            self.filename = None
        self.in_finals: bool = False
        self.teams = []
        self.fixtures: list[list[Game]] = []
        self.finals: list[list[Game]] = []
        self.fixtures_class = None
        self.finals_class = None
        self.officials = None
        self.name = ""
        self.notes = []
        if not self.filename:
            return
        self.details = {}
        self.ref = None
        self.initial_load()
        self.fixtures_gen: Generator[list[Game]] = None
        self.finals_gen: Generator[list[Game]] = None
        self.load()

    def nice_name(self):
        return self.name.lower().replace(" ", "_").replace("the_", "")

    def games_to_list(self) -> list[Game]:
        return [game for r in self.fixtures for game in r] + [game for r in self.finals for game in r]

    def ladder(self):
        return sorted(self.teams, key=lambda a: (-a.games_won, -(a.get_stats()["Point Difference"])))

    def add_team(self, team):
        if team == BYE: return
        self.teams.append(team)
        team.tournament = self
        for i in team.players:
            i.tournament = self

    def update_games(self):
        if not self.in_finals:
            if not self.fixtures or all([i.best_player for i in self.fixtures[-1]]):
                try:
                    n = next(self.fixtures_gen)
                    if n is not None:
                        self.fixtures.append(n)
                except Exception as e:  # this has to be broad because of lachies code >:(
                    logger.info("Entering Finals!")
                    self.in_finals = True
                    n = next(self.finals_gen)
                    if n is not None:
                        self.finals.append(n)
        elif all([i.best_player for i in self.finals[-1]]):
            try:
                logger.info("Next round of finals")
                n = next(self.finals_gen)
                if n is not None:
                    self.finals.append(n)
                logger.info(self.finals[-1])
            except StopIteration:
                logger.info("Last Game has been added")
        self.appoint_umpires()
        self.assign_rounds()
        self.assign_ids()
        self.assign_courts()

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
            if game.primary_official != NoOfficial: continue
            teams = [i.team for i in game.teams] + ([] if not next else [i.team for i in next.teams])
            for p in sorted(self.officials, key=lambda it: it.games_officiated):
                if prev and prev.primary_official == p: continue
                if p.team and p.team in teams: continue
                game.set_primary_official(p)
                break

    def assign_rounds(self):
        for i, r in enumerate(self.fixtures):
            for j in r:
                j.round_number = i

    def assign_courts(self):
        for r in self.fixtures:
            if r[0].court != -1:
                continue
            court_one_games = sorted(r, key=lambda a: sum([i.team.court_one for i in a.teams]))
            # court_one_games = sorted(r, key=lambda a: sum([i.team.games_won for i in a.teams]))  use for preferential treatment of wins
            court_one_games = [i for i in court_one_games if not i.bye]
            halfway = False
            for i, g in enumerate(court_one_games):
                if not halfway:
                    g.court = 0
                else:
                    g.court = 1
                halfway = i + 1 >= (len(court_one_games) / 2)
        for r in self.finals:
            for g in r:
                g.court = 0

    def players(self):
        players = []
        names = []
        for t in self.teams:
            for p in t.players:
                if p.name not in names:
                    players.append(p)
                    names.append(p.name)
        return players

    def save(self):
        if not self.filename:
            return
        logger.info("Saving...")
        d: dict[str, Any] = {
            "games": [[j.as_map() for j in i if not j.super_bye] for i in self.fixtures],
            "finals": [[j.as_map() for j in i] for i in self.finals]
        }
        if self.ref:
            d["details"] = {"ref": self.ref}
        else:
            d["details"] = {
                "fixtures_generator": self.fixtures_class.get_name(),
                "finals_generator": self.finals_class.get_name(),
                "name": self.name,
                "teams": [i.name for i in self.teams],
                "officials": [i.name for i in self.officials]
            }
        with open(self.filename, "w+") as fp:
            json.dump(d, fp, indent=4, sort_keys=True)

    def dump(self):
        self.fixtures = []
        self.finals = []
        self.save()
        self.load()

    def load(self):
        if not self.filename:
            return
        [i.reset() for i in self.teams]
        self.fixtures_gen: Generator[list[Game]] = self.fixtures_class.get_generator()
        self.finals_gen: Generator[list[Game]] = self.finals_class.get_generator()
        self.fixtures = []
        self.finals = []
        self.in_finals = False
        with open(f"{self.filename}", "r+") as fp:
            data = json.load(fp)
        self.update_games()
        for i, r in enumerate(data.get("games", [])):
            for j, g in enumerate([Game.from_map(j, self) for j in r]):
                self.update_games()
                self.fixtures[i][j] = g

        for i, r in enumerate([[Game.from_map(j, self) for j in i] for i in data.get("finals", [])]):
            for j, g in enumerate(r):
                self.finals[i][j] = g
                self.update_games()
        self.assign_ids()
        self.assign_rounds()
        self.assign_courts()
        self.appoint_umpires()
        self.update_games()

    def initial_load(self):
        if not self.filename:
            return
        self.teams = []
        with open(f"{self.filename}", "r+") as fp:
            self.details = json.load(fp)["details"]

        if "ref" in self.details:
            self.ref = self.details['ref']
            with open(f"./config/templates/{self.ref}.json", "r+") as fp:
                self.details = json.load(fp)
        with open("./config/teams.json", "r+") as fp:
            teams = json.load(fp)

            if self.details["teams"] == "all":
                self.teams = [Team.find_or_create(self, k, [Player.find_or_create(self, j) for j in v]) for k, v in teams.items()]
            else:
                self.teams = []
                for i in self.details["teams"]:
                    players = [Player.find_or_create(self, i) for i in teams[i]]
                    self.teams.append(Team.find_or_create(self, i, players))

        self.officials: list[Official] = get_officials(self)

        for i in self.teams:
            i.tournament = self
            for j in i.players:
                j.tournament = self
        self.fixtures_class = get_type_from_name(self.details["fixtures_generator"])(self)
        self.finals_class = get_type_from_name(self.details["finals_generator"])(self)
        self.name = self.details["name"]


def load_all_tournaments() -> dict[str, Tournament]:
    ret = {}
    for filename in os.listdir("./config/tournaments"):
        f = os.path.join("./config/tournaments", filename)
        if os.path.isfile(f):
            print(filename)
            t = Tournament(filename)
            ret[t.nice_name()] = t
            logger.info("------------------------------")

    return ret
