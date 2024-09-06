from FixtureGenerators.FixturesGenerator import FixturesGenerator
from database.models import Games
from structure import manage_game
from utils.databaseManager import DatabaseManager


class TopThreeFinals(FixturesGenerator):

    def __init__(self, tournament_id):
        super().__init__(tournament_id, fill_officials=True, editable=False, fill_courts=True)
        self.highest_team = None # insert laziness here (honestly its not even bad)
    
    def _end_of_round(self, tournament_id):
        with DatabaseManager() as c:
            round = Games.query.filter_by(tournament_id=tournament_id).order_by(Games.round.desc()).first().round
            round += 1
            finals_games = Games.query.filter_by(tournament_id=tournament_id, is_final=True).all()
            # id love to, but im not converting this to sql alchemy...
            ladder = c.execute("""
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
               IIF(games.team_one_id = teams.id, team_one_timeouts, team_two_timeouts), 0)) ASC
LIMIT 3""", (tournament_id, )).fetchall()
            if not finals_games:
                # Semi Finals (2nd vs 3rd)
                manage_game.create_game(tournament_id, ladder[1][0], ladder[2][0], is_final=True, round_number=round)
            if len(finals_games) == 1:
                # Grand Finals (1st vs winner of semi finals)
                manage_game.create_game(tournament_id, ladder[0][0], finals_games[0].winning_team_id, is_final=True, round_number=round)
            else: 
                # Grand finals have been played, end tournament
                super().end_tournament()
        