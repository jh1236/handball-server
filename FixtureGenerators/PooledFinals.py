from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manage_game
from utils.databaseManager import DatabaseManager


# [sf1, sf2], [3v3, 4v4, 5v5]
# [sf1, 3v3, sf2, 4v4, 5v5]

class PooledFinals(FixturesGenerator):
    def _end_of_round(self, tournament_id):
        with DatabaseManager() as c:
            ladder = c.execute(
                """
SELECT teams.id, tournamentTeams.pool                                                                                   

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
            pool_one = [j for j in ladder if j[1] == 0]
            pool_two = [j for j in ladder if j[1] == 1]
            finals_games = c.execute("""SELECT winning_team_id, team_one_id + team_two_id - winning_team_id FROM games WHERE 
            tournament_id = ? AND is_final = 1 AND (team_one_id = ? OR team_two_id = ?) OR (team_one_id = ? OR team_two_id = ?)""",
                                     (tournament_id,pool_one[0], pool_one[0], pool_two[0], pool_two[0])).fetchall()

        if finals_games:
            manage_game.create_game(tournament_id, finals_games[0][1], finals_games[1][1], is_final=True)
            manage_game.create_game(tournament_id, finals_games[0][0], finals_games[1][0], is_final=True)
        else:
            manage_game.create_game(tournament_id, pool_one[0], pool_two[1])
            manage_game.create_game(tournament_id, pool_one[1], pool_two[0])
            for p1, p2 in zip(pool_one[2:], pool_two[2:]):
                manage_game.create_game(tournament_id, p1, p2)
