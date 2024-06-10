from collections import defaultdict
from dataclasses import dataclass
from itertools import zip_longest

from utils.databaseManager import DatabaseManager


class FixturesGenerator:

    def __init__(self, tournament_id, *, fill_officials, editable, fill_courts):
        self.tournament_id = tournament_id
        self.editable = editable
        self.fill_officials = fill_officials
        self.fill_courts = fill_courts

    def _end_of_round(self, tournament):
        raise NotImplementedError()

    def end_of_round(self):
        self._end_of_round(self.tournament_id)
        if self.fill_officials:
            self.add_umpires()
        if self.fill_courts and False:
            self.add_courts()

    def add_courts(self):
        with DatabaseManager() as c:
            c.execute("""SELECT id FROM""")

    def add_umpires(self):
        with DatabaseManager() as c:
            games_query = c.execute(
                """SELECT games.id, round, court, official, scorer FROM games WHERE games.tournamentId = ? ORDER BY id""",
                (self.tournament_id,))
            players = c.execute("""SELECT id, gameId FROM playerGameStats WHERE tournamentId = ?""",
                                (self.tournament_id,))
            officials = c.execute(
                """SELECT
                                   officials.personId,
                                   officials.id,
                                   proficiency,
                                   COUNT(DISTINCT games.id),
                                   COUNT(SELECT games.id FROM games WHERE scorer = officials.id),
                                   COUNT(DISTINCT IIF(games.court = 0, games.id, null))                            
                                    FROM officials 
                                             INNER JOIN games on games.official = officials.id
                                             INNER JOIN tournamentOfficials ON officials.id = tournamentOfficials.officialId
                                    WHERE tournamentOfficials.tournamentId = ? 
            """,
                (self.tournament_id,)
            ).fetchall()

            @dataclass
            class Official:
                person_id: int
                official_id: int
                proficiency: int
                games_umpired: int
                games_scored: int
                court_one_games: int

            officials = [Official(*i) for i in officials]

            rounds = defaultdict(list)

            for i in games_query:
                rounds[i[1]].append([*i, [j[0] for j in players if j[1] == i[0]]])
        # id, round, court, official
        for r in rounds:
            court_one_games = [i for i in r if i[2] == 0]
            court_two_games = [i for i in r if i[2] == 1]
            for games in zip_longest(court_one_games, court_two_games):
                for g in games:
                    court_one_officials = sorted(
                        officials,
                        key=lambda it: (
                            -it.proficiency,
                            it.games_umpired,
                            it.court_one_games,
                        ),
                    )
                    court_two_officials = sorted(
                        officials,
                        key=lambda it: (
                            3 if (it.proficiency == 0) else it.proficiency,
                            it.games_umpired,
                            -it.court_one_games,
                        ),
                    )
                    #  games.id, round, court, official, scorer, [players]
                    if not g[3]:
                        continue
                    for o in court_one_officials if g[2] == 0 else court_two_officials:
                        if o.official_id in [k[3] for k in games if k]:
                            continue
                        if o.person_id in [i[5] for i in games]:
                            continue
                        c.execute("""UPDATE games SET official = ? WHERE id = ?""", (o.official_id, g[0]))
                        o.games_umpired += 1
                        o.court_one_games += g[2] == 0
                        g[3] = o.official_id
                        break
            if not self.details.get("scorer", False):
                continue
            for games in zip_longest(court_one_games, court_two_games):
                for g in games:
                    if not g:
                        continue
                    if g[3]:
                        continue
                    scorer = sorted(
                        officials,
                        key=lambda it: (
                            it.proficiency == 0,
                            it.games_umpired,
                            it.games_scored
                        ),
                    )
                    for o in scorer:
                        if o.official_id in [k[4] for k in games if k]:
                            continue
                        if o.person_id in [i[5] for i in games]:
                            continue
                        if o.official_id == g[3]:
                            continue
                        c.execute("""UPDATE games SET scorer = ? WHERE id = ?""", (o.official_id, g[0]))
                        g[4] = o.official_id
                        o.games_scored += 1
                        break
                    if not g[4]:
                        c.execute("""UPDATE games SET scorer = official WHERE id = ?""", (g[0],))


def get_type_from_name(name: str, tournament: int) -> FixturesGenerator:
    from FixtureGenerators.BasicFinals import BasicFinals
    from FixtureGenerators.OneRound import OneRound
    from FixtureGenerators.Pooled import Pooled
    from FixtureGenerators.RoundRobin import RoundRobin
    return {
        "BasicFinals": BasicFinals(tournament),
        "Pooled": Pooled(tournament),
        "RoundRobin": RoundRobin(tournament),
        "OneRound": OneRound(tournament)
    }[name]
