from collections import defaultdict
from dataclasses import dataclass
from itertools import zip_longest

from utils.databaseManager import DatabaseManager


class FixturesGenerator:

    def __init__(self, tournament_id, fill_officials):
        self.tournament_id = tournament_id
        self.fill_officials = fill_officials

    def _end_of_round(self, tournament):
        raise NotImplementedError()

    def end_of_round(self):
        self._end_of_round(self.tournament_id)
        if self.fill_officials:
            self.add_umpires()

    def add_umpires(self):
        with DatabaseManager() as c:
            games = c.execute("""SELECT id, round, court, official is null FROM games WHERE tournamentId = ? ORDER BY id""",
                              (self.tournament_id,))

            officials = c.execute(
                """SELECT
                                   officials.personId,
                                   proficiency,
                                   COUNT(DISTINCT games.id),
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
                proficiency: int
                games_umpired: int
                court_one_games: int

            officials = [Official(*i) for i in officials]

            rounds = defaultdict(list)

            for i in games:
                rounds[i[1]].append(i)
        # id, round, court, official
        for r in rounds:
            court_one_games = [i for i in r if i.court == 0]
            court_two_games = [i for i in r if i.court == 1]
            for games in zip_longest(court_one_games, court_two_games):
                teams = [gt.team for g in games if g for gt in g.teams]
                for g in games:
                    court_one = sorted(
                        officials,
                        key=lambda it: (
                            -it.proficiency,
                            it.games_umpired,
                            it.court_one_games,
                        ),
                    )
                    court_two = sorted(
                        officials,
                        key=lambda it: (
                            3 if (it.proficiency == 0) else it.proficiency,
                            it.games_umpired,
                            -it.court_one_games,
                        ),
                    )
                    if not g:
                        continue
                    if not officials[2]:
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



