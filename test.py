from structure import manageGame
from utils.databaseManager import DatabaseManager
from utils.statistics import calc_elo


def regen_elo():
    with DatabaseManager() as c:
        c.execute("""DELETE FROM eloChange""")
        request = c.execute("""SELECT id, tournamentId FROM games""").fetchall()
        for game_id, tournament_id in request:
            players = c.execute("""
SELECT games.isRanked as ranked,
       games.winningTeam = teamId as myTeamWon,
       games.teamOne <> playerGameStats.teamId as isSecond,
       ROUND(1500.0 + coalesce((SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = playerGameStats.playerid), 0), 2) as elo,
       playerId as player,
       (playerGameStats.roundsPlayed > 0) OR ((games.teamTwoScore + games.teamOneScore) = 0)
       FROM playerGameStats
         INNER JOIN games ON playerGameStats.gameId = games.id
WHERE games.id = ? ORDER BY isSecond""", (game_id,)).fetchall()
            if not players[0][0]:
                continue # the game is unranked, so doing elo stuff is silly
            elos = [0, 0]
            team_sizes = [0, 0]
            for i in players:
                if not i[5]: continue
                elos[i[2]] += i[3]
                team_sizes[i[2]] += 1
            for i, v in enumerate(team_sizes):
                if not v:
                    continue
                elos[i] /= v
            print(f"{elos = }, {game_id = }")
            for i in players:
                if not i[5]: continue
                win = i[1]
                my_team = i[2]
                player_id = i[4]
                elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
                c.execute(
                    """INSERT INTO eloChange(gameId, playerId, tournamentId, eloChange) VALUES (?, ?, ?, ?)""",
                    (game_id, player_id, tournament_id, elo_delta))


if __name__ == '__main__':
    # regen_elo()
    manageGame.create_tournament("The Sixth SUSS Championship", "Swiss", "BasicFinals",
                                 True, True, True, [93, 92, 40, 52, 96, 95, 56], [2, 4, 3, 1, 7, 9])
