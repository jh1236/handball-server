from typing import Generator

from FixtureMakers.FixturesGenerator import FixturesGenerator
from structure import manageGame
from structure.Game import Game
from FixtureMakers.FixtureMaker import FixtureMaker
from utils.databaseManager import DatabaseManager


class BasicFinals(FixturesGenerator):
    def get_generator(self, tournament_id) -> Generator[list[Game], None, None]:
        with DatabaseManager() as c:
            finals_games = c.execute("""SELECT winningTeam FROM games WHERE tournamentId = ? AND isFinal = 1""", (tournament_id,)).fetchall()
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
        if finals_games:
            manageGame.create_game(tournament_id, finals_games[0][0], finals_games[1][0], )
        else:
            manageGame.create_game(tournament_id, ladder[0][0], ladder[3][0])
            manageGame.create_game(tournament_id, ladder[1][0], ladder[2][0])







class BasicFinalsWithBronze(FixtureMaker):
    def get_generator(self) -> Generator[list[Game], None, None]:
        ladder = self.tournament.ladder()
        g1 = Game(ladder[0], ladder[3], self.tournament, True)
        g2 = Game(ladder[1], ladder[2], self.tournament, True)
        yield [g1, g2]
        yield [Game(g1.loser, g2.loser, self.tournament, True),Game(g1.winner, g2.winner, self.tournament, True)]
