from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manage_game
from utils.databaseManager import DatabaseManager


class BasicFinals(FixturesGenerator):

    def __init__(self, tournament_id):
        super().__init__(tournament_id, fill_officials=True, editable=False, fill_courts=True)

    def _end_of_round(self, tournament_id):
        with DatabaseManager() as c:
            finals_games = c.execute("""SELECT winning_team_id, teamOne + teamTwo - winning_team_id FROM games WHERE 
            tournament_id = ? AND is_final = 1""",
                                     (tournament_id,)).fetchall()
            finals_rounds = c.execute("""SELECT COUNT(*) FROM games WHERE is_final = 1 AND tournament_id = ? GROUP BY round""", (tournament_id,)).fetchall()
            ladder = c.execute(
                """
SELECT teams.id                                                                                   

FROM tournamentTeams
         INNER JOIN tournaments ON tournaments.id = tournamentTeams.tournament_id
         INNER JOIN teams ON teams.id = tournamentTeams.team_id
         LEFT JOIN games ON
    (games.team_one_id = teams.id or games.team_two_id = teams.id) AND games.tournament_id = tournaments.id
         AND games.is_bye = 0 AND games.is_final = 0
         LEFT JOIN playerGameStats
                    ON teams.id = playerGameStats.team_id AND games.id = playerGameStats.game_id
WHERE  tournaments.id = ?
GROUP BY teams.name
ORDER BY Cast(SUM(IIF(playerGameStats.player_id = teams.captain_id, teams.id = games.winning_team_id, 0)) AS REAL) /
         COUNT(DISTINCT games.id) DESC,
         SUM(playerGameStats.points_scored) - (SELECT SUM(playerGameStats.points_scored)
                                      FROM playerGameStats
                                      where playerGameStats.opponent_id = teams.id
                                        and playerGameStats.tournament_id = tournaments.id) DESC,
         SUM(playerGameStats.points_scored) DESC,
         SUM(playerGameStats.green_cards) + SUM(playerGameStats.yellow_cards) + SUM(playerGameStats.red_cards) ASC,
         SUM(playerGameStats.faults) ASC,
         SUM(playerGameStats.yellow_cards) ASC,
         SUM(playerGameStats.faults) ASC,
         SUM(IIF(playerGameStats.player_id = teams.captain_id,
               IIF(games.team_one_id = teams.id, team_one_timeouts, team_two_timeouts), 0)) ASC""",
                (tournament_id,),
            ).fetchall()
            rounds = c.execute("""SELECT MAX(round) FROM games WHERE tournament_id = ?""", (tournament_id,)).fetchone()[
                         0] + 1
        if len(finals_rounds) > 1:
            with DatabaseManager() as c:
                c.execute("""UPDATE tournaments SET finished = 1 WHERE tournaments.id = ?""", (tournament_id,))
                return
        if finals_games:
            manage_game.create_game(tournament_id, finals_games[0][1], finals_games[1][1], is_final=True, round_number=rounds)
            manage_game.create_game(tournament_id, finals_games[0][0], finals_games[1][0], is_final=True, round_number=rounds)
        else:
            manage_game.create_game(tournament_id, ladder[0][0], ladder[3][0], is_final=True,round_number=rounds)
            manage_game.create_game(tournament_id, ladder[1][0], ladder[2][0], is_final=True,round_number=rounds)
