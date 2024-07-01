from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manage_game
from utils.databaseManager import DatabaseManager


class BasicFinals(FixturesGenerator):

    def __init__(self, tournament_id):
        super().__init__(tournament_id, fill_officials=True, editable=False, fill_courts=True)

    def _end_of_round(self, tournament_id):
        with DatabaseManager() as c:
            finals_games = c.execute("""SELECT winningTeam, teamOne + teamTwo - winningTeam FROM games WHERE 
            tournamentId = ? AND isFinal = 1""",
                                     (tournament_id,)).fetchall()
            finals_rounds = c.execute("""SELECT COUNT(*) FROM games WHERE isFinal = 1 AND tournamentId = ? GROUP BY round""", (tournament_id,)).fetchall()
            ladder = c.execute(
                """
SELECT teams.id                                                                                   

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
            rounds = c.execute("""SELECT MAX(round) FROM games WHERE tournamentId = ?""", (tournament_id,)).fetchone()[
                         0] + 1
        if len(finals_rounds) > 1:
            with DatabaseManager() as c:
                c.execute("""UPDATE tournaments SET isFinished = 1 WHERE tournaments.id = ?""", (tournament_id,))
                return
        if finals_games:
            manage_game.create_game(tournament_id, finals_games[0][1], finals_games[1][1], is_final=True, round_number=rounds)
            manage_game.create_game(tournament_id, finals_games[0][0], finals_games[1][0], is_final=True, round_number=rounds)
        else:
            manage_game.create_game(tournament_id, ladder[0][0], ladder[3][0], is_final=True,round_number=rounds)
            manage_game.create_game(tournament_id, ladder[1][0], ladder[2][0], is_final=True,round_number=rounds)
