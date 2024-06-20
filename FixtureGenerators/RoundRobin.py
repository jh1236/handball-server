from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manageGame
from utils.databaseManager import DatabaseManager


class RoundRobin(FixturesGenerator):
    def __init__(self, tournament):

        super().__init__(tournament, fill_officials=True, editable=False, fill_courts=True)

    def _end_of_round(self, tournament):
        with DatabaseManager() as c:
            teams = c.execute(
                """
SELECT tournamentTeams.teamId,
coalesce((SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN teams inside ON inside.id = tournamentTeams.teamId
                                INNER JOIN people captain ON captain.id = inside.captain
                                LEFT JOIN people nonCaptain ON nonCaptain.id = inside.nonCaptain
                                LEFT JOIN people sub ON sub.id = inside.substitute
                       where eloChange.playerId = sub.id
                          or eloChange.playerId = captain.id
                          or eloChange.playerId = nonCaptain.id)
           /
                      COUNT(DISTINCT playerGameStats.playerId), 1500.0) as ord
FROM tournamentTeams
LEFT JOIN playerGameStats ON playerGameStats.teamId = tournamentTeams.teamId
WHERE  tournamentTeams.tournamentId = ?
GROUP BY tournamentTeams.teamId
ORDER BY ord""",
                (tournament,),
            ).fetchall()
            rounds = (c.execute("""SELECT MAX(round) FROM games WHERE tournamentId = ?""", (tournament,)).fetchone()[0] or 0) + 1

        teams = [i[0] for i in teams]
        if len(teams) % 2 != 0:
            teams += [1]
        if len(teams) <= rounds:
            with DatabaseManager() as c:
                c.execute("""UPDATE tournaments SET inFinals = 1 WHERE tournaments.id = ?""", (tournament,))
            return
        print(teams)

        for _ in range(rounds - 1):
            # Rotate the teams except the first one
            teams[1:] = [teams[-1]] + teams[1:-1]
        print(teams)

        mid = len(teams) // 2
        for j in range(mid):
            team_one = teams[j]
            team_two = teams[len(teams) - 1 - j]
            manageGame.create_game(tournament, team_one, team_two, round_number=rounds)
