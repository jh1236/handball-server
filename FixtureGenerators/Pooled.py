from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manage_game
from utils.databaseManager import DatabaseManager


class Pooled(FixturesGenerator):

    def __init__(self, tournament_id):
        super().__init__(tournament_id, fill_officials=True, editable=False, fill_courts=True)

    def _begin_tournament(self, tournament_id):
        with DatabaseManager() as c:
            teams = c.execute(
                """
SELECT tournamentTeams.team_id, pool,
coalesce((SELECT SUM(elo_delta)
                       from eloChange
                                INNER JOIN teams inside ON inside.id = tournamentTeams.team_id
                                INNER JOIN people captain ON captain.id = inside.captain_id
                                LEFT JOIN people nonCaptain ON nonCaptain.id = inside.non_captain_id
                                LEFT JOIN people sub ON sub.id = inside.substitute_id
                       where eloChange.player_id = sub.id
                          or eloChange.player_id = captain.id
                          or eloChange.player_id = nonCaptain.id)
           /
                      COUNT(DISTINCT playerGameStats.player_id), 1500.0) as o                                                                                  

FROM tournamentTeams
LEFT JOIN playerGameStats ON playerGameStats.team_id = tournamentTeams.team_id
WHERE  tournamentTeams.tournament_id = ?
GROUP BY tournamentTeams.team_id
ORDER BY o""",
                (tournament_id,),
            ).fetchall()
            pool = 0
            for i in teams:
                c.execute("""UPDATE tournamentTeams SET pool = ? WHERE team_id = ? AND tournament_id = ?""", (pool, i, tournament_id))
                pool = 1 - pool
            c.execute("""UPDATE tournaments SET tournaments.is_pooled = 1 WHERE id = ?""", (tournament_id,))

    def _end_of_round(self, tournament_id):
        with DatabaseManager() as c:
            teams = c.execute(
                """
SELECT tournamentTeams.team_id, pool                                                                                  

FROM tournamentTeams

WHERE  tournamentTeams.tournament_id = ?
GROUP BY tournamentTeams.team_id
ORDER BY team_id""",
                (tournament_id,),
            ).fetchall()
            rounds = c.execute("""SELECT MAX(round) FROM games WHERE tournament_id = ?""", (tournament_id,)).fetchone()[
                0] or 0

        pools = [[j for j in teams if j[1] == i] for i in range(2)]

        for pool in pools:
            if len(pool) % 2 != 0:
                pool += [1]

        if max(len(i) for i in pools) <= rounds + 1:
            with DatabaseManager() as c:
                c.execute("""UPDATE tournaments SET in_finals = 1 WHERE tournaments.id = ?""", (tournament_id,))
            return
        for _ in range(rounds):
            for pool in pools:
                pool[1:] = [pool[-1]] + pool[1:-1]
            # Rotate the teams except the first one
        for pool in pools:
            mid = len(pool) // 2
            for j in range(mid):
                team_one = pool[j]
                team_two = pool[len(pool) - 1 - j]
                manage_game.create_game(tournament_id, team_one, team_two, round_number=rounds + 1)
