from collections import defaultdict
from dataclasses import dataclass
from itertools import zip_longest
from math import ceil

from utils.databaseManager import DatabaseManager


class FixturesGenerator:

    def __init__(self, tournament_id, *, fill_officials, editable, fill_courts):
        self.tournament_id = tournament_id
        self.editable = editable
        self.fill_officials = fill_officials
        self.fill_courts = fill_courts

    def manual_allowed(self):
        return self.editable

    def _end_of_round(self, tournament):
        raise NotImplementedError()

    def _begin_tournament(self, tournament_id):
        pass

    def end_of_round(self):
        self._end_of_round(self.tournament_id)
        if self.fill_courts:
            self.add_courts()
        if self.fill_officials:
            self.add_umpires()

    def add_courts(self):
        with DatabaseManager() as c:
            games_query = c.execute("""
SELECT games.id,
       games.round,
       games.isFinal,
       coalesce(CAST(SUM(otherGames.winningTeam = teams.id) AS REAL), 0) / max(COUNT(otherGames.id), 1) as o
FROM games
         INNER JOIN teams ON (teams.id = games.teamOne OR teams.id = games.teamTwo)
         LEFT JOIN games otherGames ON (teams.id = otherGames.teamOne OR teams.id = otherGames.teamTwo) AND
                                       games.tournamentId = otherGames.tournamentId AND otherGames.id < games.id
WHERE games.tournamentId = ?  AND games.started = 0 AND games.isBye = 0 AND games.round = (SELECT MAX(round) FROM games inn WHERE inn.tournamentId = games.tournamentId AND not inn.isFinal)
GROUP by games.id
ORDER BY games.round, o DESC""", (self.tournament_id,)).fetchall()
            games = [i for i in games_query if not i[2]]
            finals = [i for i in games_query if i[2]]
            l = ceil(len(games) / 2) - 1
            for i, g in enumerate(games):
                c.execute("""UPDATE games SET court = ? WHERE id = ?""", (i > l, g[0]))
            for i in finals:
                c.execute("""UPDATE games SET court = 0 WHERE id = ?""", (i[0]))

    def begin_tournament(self):
        self._begin_tournament(self.tournament_id)
        self.end_of_round()

    def add_umpires(self):
        with DatabaseManager() as c:
            games_query = c.execute(
                """SELECT games.id, round, court, official_id, scorer_id FROM games WHERE games.tournamentId = ? AND games.isBye = 0 ORDER BY id""",
                (self.tournament_id,)).fetchall()
            players = c.execute(
                """SELECT playerGameStats.playerId, gameId FROM playerGameStats WHERE tournamentId = ?""",
                (self.tournament_id,)).fetchall()
            scorer = c.execute("""SELECT hasScorer FROM tournaments WHERE id = ?""",
                               (self.tournament_id,)).fetchone()[0]
            officials = c.execute(
                """
SELECT officials.personId,
       officials.id,
       officials.proficiency,
       COUNT(DISTINCT games.id),
       COUNT((SELECT games.id FROM games WHERE scorer_id = officials.id)),
       COUNT(DISTINCT IIF(games.court = 0, games.id, null))
FROM officials
         INNER JOIN tournamentOfficials ON officials.id = tournamentOfficials.officialId
         LEFT JOIN games on games.official_id = officials.id AND games.tournamentId = tournamentOfficials.tournamentId
WHERE tournamentOfficials.tournamentId = ?
GROUP BY officials.id""",
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

        print([(i) for i in officials])
        officials = [Official(*i) for i in officials]
        print([(i.person_id, i.proficiency) for i in officials])
        rounds = defaultdict(list)
        game_to_players = defaultdict(list)
        for i in players:
            game_to_players[i[1]].append(i[0])
        for i in games_query:
            rounds[i[1]].append(list(i))
        rounds = list(rounds.values())
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
                    print(f"c1: {[(i.person_id, i.proficiency) for i in court_one_officials]}, c2: {[(i.person_id, i.proficiency) for i in court_two_officials]}")
                    #  games.id, round, court, official, scorer, [players]

                    if not g:
                        continue
                    if g[3]:
                        continue
                    for o in court_one_officials if g[2] == 0 else court_two_officials:
                        if o.official_id in [k[3] for k in games if k]:
                            # the official is already umpiring this round
                            continue
                        if any([o.person_id in [j for j in game_to_players[i[0]]] for i in games if i]):
                            # the official is playing this round
                            continue
                        with DatabaseManager() as c:
                            c.execute("""UPDATE games SET official_id = ? WHERE id = ?""", (o.official_id, g[0]))
                        o.games_umpired += 1
                        o.court_one_games += g[2] == 0
                        g[3] = o.official_id
                        break
            if not scorer:
                continue
            for games in zip_longest(court_one_games, court_two_games):
                for g in games:
                    if not g:
                        continue
                    if g[4]:
                        continue
                    scorer = sorted(
                        officials,
                        key=lambda it: (
                            it.proficiency == 0,
                            it.games_umpired,
                            it.games_scored
                        ),
                    )
                    print(f"{[(i.person_id, i.proficiency) for i in scorer]}")
                    for o in scorer:
                        if o.official_id in [k[3] for k in games if k]:
                            # the official is umpiring this round
                            continue
                        if o.official_id in [k[4] for k in games if k]:
                            # the official is already scoring this round
                            continue
                        if any([o.person_id in [j for j in game_to_players[i[0]]] for i in games if i]):
                            # the official is playing this round
                            continue
                        with DatabaseManager() as c:
                            c.execute("""UPDATE games SET scorer_id = ? WHERE id = ?""", (o.official_id, g[0]))
                        g[4] = o.official_id
                        o.games_scored += 1
                        break
                    if not g[4]:
                        # there was no scorer found, set the scorer to be equal to the umpire
                        with DatabaseManager() as c:
                            c.execute("""UPDATE games SET scorer_id = official_id WHERE id = ?""", (g[0],))


def get_type_from_name(name: str, tournament: int) -> FixturesGenerator:
    from FixtureGenerators.BasicFinals import BasicFinals
    from FixtureGenerators.OneRound import OneRound
    from FixtureGenerators.Pooled import Pooled
    from FixtureGenerators.RoundRobin import RoundRobin
    from FixtureGenerators.Swiss import Swiss
    return {
        "BasicFinals": BasicFinals(tournament),
        "Pooled": Pooled(tournament),
        "RoundRobin": RoundRobin(tournament),
        "OneRoundEditable": OneRound(tournament),
        "Swiss": Swiss(tournament)
    }[name]
