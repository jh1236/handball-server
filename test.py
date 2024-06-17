from utils.databaseManager import DatabaseManager
from utils.statistics import calc_elo


def regen_elo():
    with DatabaseManager() as c:
        c.execute("""DELETE FROM eloChange""")
        request = c.execute("""SELECT id, tournamentId FROM games""").fetchall()
        for game_id, tournament_id in request:
            teams = c.execute("""
SELECT games.isRanked as ranked,
       games.winningTeam = teamId as myTeamWon,
       games.teamOne <> playerGameStats.teamId as isSecond,
       ROUND(1500.0 + coalesce((SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = playerGameStats.playerid), 0), 2) as elo,
       playerId as player
       FROM playerGameStats
         INNER JOIN games ON playerGameStats.gameId = games.id
WHERE games.id = ? ORDER BY isSecond""", (game_id,)).fetchall()
            if teams[0][0]:  # the game is unranked, so doing elo stuff is silly
                elos = [0, 0]
                team_sizes = [0, 0]
                for i in teams:
                    elos[i[2]] += i[3]
                    team_sizes[i[2]] += 1
                for i, v in enumerate(team_sizes):
                    if not v:
                        continue
                    elos[i] /= v
                print(f"{elos = }, {game_id = }")
                for i in teams:
                    win = i[1]
                    my_team = i[2]
                    player_id = i[4]
                    elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
                    c.execute(
                        """INSERT INTO eloChange(gameId, playerId, tournamentId, eloChange) VALUES (?, ?, ?, ?)""",
                        (game_id, player_id, tournament_id, elo_delta))


if __name__ == '__main__':
    regen_elo()
    # manageGame.create_tournament("Test", "RoundRobin", "BasicFinals",
    #                              True, True, True, [52, 13, 40, 4, 28, 22, 26, 37, 6], [2, 4, 3, 1])
