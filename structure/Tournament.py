import json
import os
from itertools import zip_longest
from typing import Generator, Any

from FixtureMakers.FixtureMaker import get_type_from_name
from FixtureMakers.Pooled import Pooled
from structure.Game import Game
from structure.OfficiatingBody import Official, get_officials, NoOfficial
from structure.Player import Player, elo_map
from structure.Team import Team, BYE
from utils.logging_handler import logger
from utils.util import n_chunks, initial_elo
from itertools import permutations

officials_permuted = []


class Tournament:
    def __init__(self, file: str):
        if file != "-":
            self.filename = f"./config/tournaments/{file}"
        else:
            self.filename = False
        self.in_finals: bool = False
        self.teams: list[Team] = []
        self.fixtures: list[list[Game]] = []
        self.finals: list[list[Game]] = []
        self.fixtures_class = None
        self.finals_class = None
        self.officials: list[Official] = []
        self.name = ""
        self.notes = ""
        self.two_courts = False
        if not self.filename:
            return
        self.details = {}
        self.ref = None
        self.initial_load()
        self.fixtures_gen: Generator[list[Game]] = None
        self.finals_gen: Generator[list[Game]] = None
        self.load()

    def nice_name(self):
        return self.name.lower().replace(" ", "_").replace("the_", "").replace("'", "")

    def games_to_list(self) -> list[Game]:
        return [game for r in self.fixtures for game in r] + [
            game for r in self.finals for game in r
        ]

    def ladder(self):
        if isinstance(self.fixtures_class, Pooled):
            pools = list(n_chunks(sorted(self.teams, key=lambda it: it.nice_name()), 2))
            return [
                sorted(
                    [j for j in i if "bye" not in j.nice_name()],
                    key=lambda a: (
                        -a.percentage,
                        -a.point_difference,
                        -a.points_for,
                        -a.games_won,
                        a.cards,
                        a.red_cards,
                        a.yellow_cards,
                        a.faults,
                        a.timeouts,
                        a.nice_name(),
                    ),
                )
                for i in pools
            ]
        else:
            return sorted(
                [j for j in self.teams if "bye" not in j.nice_name()],
                key=lambda a: (
                    -a.percentage,
                    -a.point_difference,
                    -a.points_for,
                    -a.games_won,
                    a.cards,
                    a.red_cards,
                    a.yellow_cards,
                    a.faults,
                    a.timeouts,
                    a.nice_name(),
                ),
            )

    def add_team(self, team):
        if team == BYE:
            return
        self.teams.append(team)
        team.tournament = self
        for i in team.players:
            i.tournament = self
        self.teams.sort(key=lambda a: a.nice_name())

    def no_games_to_play(self):
        return any([not i.bye for i in self.fixtures[-1]]) and all(
            [i.best_player for i in self.fixtures[-1]]
        )

    def update_games(self, generator_value=None):
        if not self.in_finals:
            while (
                not self.fixtures
                or self.no_games_to_play()
                or generator_value is not None
            ) and not self.in_finals:
                try:
                    n = self.fixtures_gen.send(generator_value)
                    if n is not None:
                        self.fixtures.append(n)
                except StopIteration as e:
                    logger.info("Entering Finals!")
                    self.in_finals = True
                    n = next(self.finals_gen)
                    if n is not None:
                        self.finals.append(n)
                generator_value = None
        else:
            if (
                all([i.best_player for i in self.finals[-1]])
                or generator_value is not None
            ):
                try:
                    logger.info("Next round of finals")
                    n = next(self.finals_gen)
                    if n is not None:
                        self.finals.append(n)
                    logger.info(self.finals[-1])
                except StopIteration:
                    logger.info("Last Game has been added")
        for i, g in enumerate(self.games_to_list()):
            g.id = i
        self.assign_courts()
        self.appoint_umpires()
        self.assign_rounds()

    def get_game(self, game_id: int) -> Game:
        self.update_games()
        if game_id >= len(self.games_to_list()):
            raise ValueError(f"Game index {game_id} out of bounds.")
        if game_id < 0:
            return self.games_to_list()[game_id]
        return next(i for i in self.games_to_list() if i.id == game_id)

    def appoint_umpires(self):
        for r in self.fixtures:
            court_one_games = [i for i in r if i.court == 0]
            court_two_games = [i for i in r if i.court == 1]
            for games in zip_longest(court_one_games, court_two_games):
                teams = [gt.team for g in games if g for gt in g.teams]
                for g in games:
                    court_one = sorted(
                        self.officials,
                        key=lambda it: (
                            -it.level,
                            it.internal_games_umpired,
                            it.games_court_one,
                        ),
                    )
                    court_two = sorted(
                        self.officials,
                        key=lambda it: (
                            3 if (it.level == 0) else it.level,
                            it.internal_games_umpired,
                            -it.games_court_one,
                        ),
                    )
                    if not g:
                        continue
                    if g.primary_official != NoOfficial:
                        continue
                    for o in court_one if g.court == 0 else court_two:
                        if o in [k.primary_official for k in games if k]:
                            continue
                        if any([i in teams for i in o.team]):
                            continue
                        g.set_primary_official(o)
                        break
            if not self.details.get("scorer", False):
                continue
            for games in zip_longest(court_one_games, court_two_games):
                teams = [gt.team for g in games if g for gt in g.teams]
                for g in games:
                    if not g:
                        continue
                    if g.scorer != NoOfficial:
                        continue
                    scorer = sorted(
                        self.officials,
                        key=lambda it: (
                            it.level == 0,
                            it.internal_games_scored,
                            it.internal_games_umpired,
                        ),
                    )
                    for o in scorer:
                        if o in [k.primary_official for k in games if k]:
                            continue
                        if o in [k.scorer for k in games if k]:
                            continue
                        if any([i in teams for i in o.team]):
                            continue
                        g.set_scorer(o)
                        break
                    if g.scorer == NoOfficial:
                        g.set_scorer(g.primary_official)
        for r in self.finals:
            court_one_games = [i for i in r if i.court == 0]
            court_two_games = [i for i in r if i.court == 1]
            for games in zip_longest(court_one_games, court_two_games):
                teams = [gt.team for g in games if g for gt in g.teams]
                for g in games:
                    finals = [
                        i
                        for i in sorted(
                            self.officials,
                            key=lambda it: it.internal_games_umpired,
                        )
                        if i.level == 2
                    ]
                    other = sorted(
                        self.officials,
                        key=lambda it: (it.level != 0, it.internal_games_umpired),
                    )
                    if not g:
                        continue
                    if g.primary_official != NoOfficial:
                        continue
                    for o in other if g.court == 1 else finals:
                        if o in [k.primary_official for k in games if k]:
                            continue
                        if any([i in teams for i in o.team]):
                            continue
                        g.set_primary_official(o)
                        break
            if not self.details.get("scorer", False):
                continue
            for games in zip_longest(court_one_games, court_two_games):
                teams = [gt.team for g in games if g for gt in g.teams]
                for g in games:
                    if not g:
                        continue
                    if g.scorer != NoOfficial:
                        continue
                    scorer = sorted(
                        self.officials,
                        key=lambda it: (
                            it.internal_games_scored,
                            it.internal_games_umpired,
                        ),
                    )
                    for o in scorer:
                        if o in [k.primary_official for k in games if k]:
                            continue
                        if o in [k.scorer for k in games if k]:
                            continue
                        if any([i in teams for i in o.team]):
                            continue
                        g.set_scorer(o)
                        break
                    if g.scorer == NoOfficial:
                        g.set_scorer(g.primary_official)

    def assign_rounds(self):
        for i, r in enumerate(self.fixtures):
            for j in r:
                j.round_number = i
        for i, r in enumerate(self.finals):
            for j in r:
                j.round_number = i

    def assign_courts(self):
        for r in self.fixtures:
            if not r or r[0].court != -1:
                continue
            # court_one_games = sorted(r, key=lambda a: sum([i.team.court_one for i in a.teams]))
            court_one_games = sorted(
                r,
                key=lambda a: -sum(
                    [i.team.games_won / (i.team.games_played or 1) for i in a.teams]
                ),
            )  # use for preferential treatment of wins
            court_one_games = [i for i in court_one_games if not i.bye]
            halfway = False
            for i, g in enumerate(court_one_games):
                if not halfway:
                    g.court = 0
                else:
                    g.court = 1
                halfway = i + 1 >= (len(court_one_games) / 2) and self.two_courts
        for r in self.finals:
            for g in r:
                if g.court == -1:
                    g.court = 0

    def players(self):
        players = {}
        names = []
        for t in self.teams:
            for p in t.players:
                if p.name not in names:
                    p1 = Player(p.name)
                    p1.tournament = self
                    players[p.name] = p1
                    names.append(p.name)
                players[p.name].add_stats(p.get_stats_detailed())
        return list(players.values())

    def save(self, location=None):
        if location is None:
            location = self.filename
        if not location:
            return
        logger.info("Saving...")
        d: dict[str, Any] = {
            "games": [
                [j.as_map() for j in i if not j.super_bye] for i in self.fixtures
            ],
            "finals": [[j.as_map() for j in i] for i in self.finals],
            "notes": self.notes,
        }
        if self.ref:
            d["details"] = {"ref": self.ref}
        else:
            d["details"] = {
                "fixtures_generator": self.fixtures_class.get_name(),
                "finals_generator": self.finals_class.get_name(),
                "name": self.name,
                "teams": "all"
                if self.details["teams"] == "all"
                else [i.name for i in self.teams],
                "officials": "all"
                if self.details["officials"] == "all"
                else [i.name for i in self.officials],
                "twoCourts": self.two_courts,
                "ranked": self.details.get("ranked", True),
            }
        with open(location, "w+") as fp:
            json.dump(d, fp, indent=4, sort_keys=True)

    def dump(self):
        self.fixtures = []
        self.finals = []
        self.save()
        self.load()

    # TODO: Rewrite this god forsaken code this is actually horrible
    def load(self):
        if not self.filename:
            return
        [i.reset() for i in self.teams]
        [i.reset() for i in self.officials]
        self.fixtures_gen: Generator[list[Game]] = self.fixtures_class.get_generator()
        self.finals_gen: Generator[list[Game]] = self.finals_class.get_generator()
        self.fixtures = []
        self.finals = []
        self.in_finals = False
        with open(f"{self.filename}", "r+") as fp:
            data = json.load(fp)
        cursed = None  # HACK: OH GOD OH WHY THIS IS BEGGING TO BE REWRITTEN
        # FUTURE: nvm senpai Lachie agreed that its the best code he's ever seen
        for i, r in enumerate(data.get("games", [])):
            self.update_games(cursed)
            cursed = True
            for j, m in enumerate(r):
                g = Game.from_map(m, self)
                self.fixtures[i][j] = g
        for i, r in enumerate(data.get("finals", [])):
            for j, m in enumerate(r):
                self.update_games()
                g = Game.from_map(m, self, True)
                self.finals[i][j] = g
        self.assign_rounds()
        self.assign_courts()
        self.appoint_umpires()
        self.update_games()

    def initial_load(self):
        if not self.filename:
            return
        self.teams = []
        with open(f"{self.filename}", "r+") as fp:
            dic = json.load(fp)
            self.details = dic["details"]
            self.notes = dic.get("notes", "")

        if "ref" in self.details:
            self.ref = self.details["ref"]
            with open(f"./config/templates/{self.ref}.json", "r+") as fp:
                self.details = json.load(fp)
        with open("./config/signups/teams.json", "r+") as fp:
            teams = json.load(fp)
            with open("./config/teams.json", "r+") as fp2:
                teams = teams | json.load(fp2)

        key = self.details["teams"]

        if self.details["teams"] == "signup":
            with open("./config/signups/teams.json", "r+") as fp:
                key = json.load(fp).keys()

        if self.details["teams"] == "all":
            self.teams = []
            for k, v in teams.items():
                if isinstance(v, list):
                    team = Team.find_or_create(self, k, [Player(j) for j in v])
                else:
                    team = Team.find_or_create(
                        self, k, [Player(j).set_tournament(self) for j in v["players"]]
                    )
                    team.primary_color = v["colors"][0]
                    team.secondary_color = v["colors"][1]
                self.teams.append(team)
        else:
            self.teams = []
            for i in key:
                if isinstance(teams[i], list):
                    players = [
                        Player(j).set_tournament(self) for c, j in enumerate(teams[i])
                    ]
                    team = Team.find_or_create(self, i, players)
                else:
                    players = [
                        Player(j).set_tournament(self)
                        for c, j in enumerate(teams[i]["players"])
                    ]
                    team = Team.find_or_create(self, i, players)
                    team.primary_color = teams[i]["colors"][0]
                    team.secondary_color = teams[i]["colors"][1]
                self.teams.append(team)
        self.teams.sort(key=lambda a: a.nice_name())
        self.two_courts = self.details["twoCourts"]
        self.officials: list[Official] = get_officials(self)

        for i in self.teams:
            i.tournament = self
            for j in i.players:
                j.tournament = self
        self.fixtures_class = get_type_from_name(self.details["fixtures_generator"])(
            self
        )
        self.finals_class = get_type_from_name(self.details["finals_generator"])(self)
        self.name = self.details["name"]


def load_all_tournaments() -> dict[str, Tournament]:
    ret = {}
    for i in elo_map:
        elo_map[i] = initial_elo
    with open("./config/tournaments.txt") as fp:
        files = fp.readlines()
    for i, filename in enumerate(files):
        filename = filename.replace("\n", "") + ".json"
        f = os.path.join("./config/tournaments", filename)
        if os.path.isfile(f):
            t = Tournament(filename)
            t.details["sort"] = i
            ret[t.nice_name()] = t
            logger.info("------------------------------")

    return ret
