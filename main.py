from structure import Team
import tournaments

if __name__ == "__main__":
    teams = []
    for i in range(8):
        teams.append(Team(f"Team {i}"))
    comp = tournaments.pooled(teams, 3)
    games = 0
    for game in comp:
        print(game)
        games += 1
        game.team_one_wins()
    print(f"Total Matches: {games}")
