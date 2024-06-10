import itertools

from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manageGame
from utils.databaseManager import DatabaseManager
from utils.util import n_chunks
from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker


# [sf1, sf2], [3v3, 4v4, 5v5]
# [sf1, 3v3, sf2, 4v4, 5v5]

class PooledFinals(FixturesGenerator):
    def _end_of_round(self, tournament_id):
        with DatabaseManager() as c:
            ladder = c.execute(
                """
SELECT teams.id, tournamentTeams.pool                                                                                   

FROM tournamentTeams
         INNER JOIN tournaments ON tournaments.id = tournamentTeams.tournamentId
         INNER JOIN teams ON teams.id = tournamentTeams.teamId
         LEFT JOIN games ON
    (games.teamOne = teams.id or games.teamTwo = teams.id) AND games.tournamentId = tournaments.id
         AND games.isBye = 0 AND games.isFinal = 0
         LEFT JOIN playerGameStats
                    ON teams.id = playerGameStats.teamId AND games.id = playerGameStats.gameId
WHERE  tournaments.id = ?
GROUP BY teams.name
ORDER BY Cast(SUM(IIF(playerGameStats.playerId = teams.captain, teams.id = games.winningTeam, 0)) AS REAL) /
         COUNT(DISTINCT games.id) DESC,
         SUM(playerGameStats.points) - (SELECT SUM(playerGameStats.points)
                                      FROM playerGameStats
                                      where playerGameStats.opponentId = teams.id
                                        and playerGameStats.tournamentId = tournaments.id) DESC,
         SUM(playerGameStats.points) DESC,
         SUM(playerGameStats.greenCards) + SUM(playerGameStats.yellowCards) + SUM(playerGameStats.redCards) ASC,
         SUM(playerGameStats.faults) ASC,
         SUM(playerGameStats.yellowCards) ASC,
         SUM(playerGameStats.faults) ASC,
         SUM(IIF(playerGameStats.playerId = teams.captain,
               IIF(games.teamOne = teams.id, teamOneTimeouts, teamTwoTimeouts), 0)) ASC""",
                (tournament_id,),
            ).fetchall()
            pool_one = [j for j in ladder if j[1] == 0]
            pool_two = [j for j in ladder if j[1] == 1]
            finals_games = c.execute("""SELECT winningTeam, teamOne + teamTwo - winningTeam FROM games WHERE 
            tournamentId = ? AND isFinal = 1 AND (teamOne = ? OR teamTwo = ?) OR (teamOne = ? OR teamTwo = ?)""",
                                     (tournament_id,pool_one[0], pool_one[0], pool_two[0], pool_two[0])).fetchall()

        if finals_games:
            manageGame.create_game(tournament_id, finals_games[0][1], finals_games[1][1], is_final=True)
            manageGame.create_game(tournament_id, finals_games[0][0], finals_games[1][0], is_final=True)
        else:
            manageGame.create_game(tournament_id, pool_one[0], pool_two[1])
            manageGame.create_game(tournament_id, pool_one[1], pool_two[0])
            for p1, p2 in zip(pool_one[2:], pool_two[2:]):
                manageGame.create_game(tournament_id, p1, p2)
