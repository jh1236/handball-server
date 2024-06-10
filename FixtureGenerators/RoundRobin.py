from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manageGame
from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker
from utils.databaseManager import DatabaseManager


class RoundRobin(FixturesGenerator):
    def _end_of_round(self, tournament):
        with DatabaseManager() as c:
            teams = c.execute(
                """
SELECT tournamentTeams.teamId                                                                                  

FROM tournamentTeams
INNER JOIN playerGameStats ON playerGameStats.teamId = tournamentTeams.teamId
WHERE  tournamentTeams.tournamentId = ?
GROUP BY tournamentTeams.teamId
ORDER BY (SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN teams inside ON inside.id = tournamentTeams.teamId
                                INNER JOIN people captain ON captain.id = inside.captain
                                LEFT JOIN people nonCaptain ON nonCaptain.id = inside.nonCaptain
                                LEFT JOIN people sub ON sub.id = inside.substitute
                       where eloChange.playerId = sub.id
                          or eloChange.playerId = captain.id
                          or eloChange.playerId = nonCaptain.id)
           /
                      COUNT(DISTINCT playerGameStats.playerId)""",
                (tournament,),
            ).fetchall()
            rounds = c.execute("""SELECT MAX(round) FROM games WHERE tournamentId = ?""", (tournament,)).fetchone()[0]

        if len(teams) % 2 != 0:
            teams += [1]

        if len(teams) >= rounds:
            with DatabaseManager() as c:
                c.execute("""UPDATE tournaments SET inFinals = 1 WHERE tournaments.id = ?""", (tournament,))
            return

        for _ in range(rounds):
            # Rotate the teams except the first one
            teams[1:] = [teams[-1]] + teams[1:-1]

        mid = len(teams) // 2
        for j in range(mid):
            team_one = teams[j]
            team_two = teams[len(teams) - 1 - j]
            manageGame.create_game(tournament, team_one, team_two)
