from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manage_game
from utils.databaseManager import DatabaseManager


class RoundRobin(FixturesGenerator):
    def __init__(self, tournament):

        super().__init__(tournament, fill_officials=True, editable=False, fill_courts=True)

    def _end_of_round(self, tournament):
        with DatabaseManager() as c:
            teams = c.execute(
                """
SELECT tournamentTeams.team_id
FROM tournamentTeams
LEFT JOIN playerGameStats ON playerGameStats.team_id = tournamentTeams.team_id
WHERE  tournamentTeams.tournament_id = ?
GROUP BY tournamentTeams.team_id
ORDER BY tournamentTeams.team_id""",
                (tournament,),
            ).fetchall()
            rounds = (c.execute("""SELECT MAX(round) FROM games WHERE tournament_id = ?""", (tournament,)).fetchone()[0] or 0) + 1

        teams = [i[0] for i in teams]
        if len(teams) % 2 != 0:
            teams += [1]
        if len(teams) <= rounds:
            with DatabaseManager() as c:
                c.execute("""UPDATE tournaments SET in_finals = 1 WHERE tournaments.id = ?""", (tournament,))
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
            manage_game.create_game(tournament, team_one, team_two, round_number=rounds)
