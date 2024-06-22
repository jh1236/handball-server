from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manageGame
from utils.databaseManager import DatabaseManager
from collections import defaultdict
from math import log2,ceil
class Swiss(FixturesGenerator):
    def __init__(self, tournament):

        super().__init__(tournament, fill_officials=True, editable=False, fill_courts=True)
    
    def __can_be_played(self, history, team_one, team_two):
        if (team_one, team_two) in history or (team_two, team_one) in history:
            return False
        return True

    def brute_force(self, history, teams):
        # This is a brute force algorithm that will try to find a bracket that works
        # It will try to find a bracket that works by trying all possible combinations
        games = []
        while len(teams) >= 2:
            team1 = teams.pop(0)
            for team2 in teams:
                if self.__can_be_played(history, team1, team2):
                    games.append((team1, team2))
                    # Remove the teams from the list
                    teams.remove(team2)
                    break
        return games, teams   
    
    def find_bracket(self, previousGames, _teams):
        teams = [x[0] for x  in _teams]
        p = []
        f = []
        games = []
        for j in _teams:
            p.append(j[0])
            f.append(j[1])
        priority = [x for _, x in sorted(zip(f, p))] # sort to find the teams we care most about
        priority = [x for x in priority if x != None]
        while len(priority) >= 2:
            initial = teams.index(priority.pop(0))
            team1 = teams.pop(initial)
            found = False
            for j in range(len(teams)):
                index = (initial + j) % len(teams) # to match teams with the same "skill" level, while prioritising players
                team2 = teams[index]

                if self.__can_be_played(previousGames, team1, team2) and team1 != team2 and team2 and team1:
                    games += [(team1, team2)]
                    # remove the team from the priority list as well
                    found = True
                    print(team2)
                    priority.remove(team2)
                    teams.remove(team2)
                    break
            if found == False:
                # shit broke, time to brute force :cries:
                games, teams = self.brute_force(previousGames, [x for _, x in sorted(zip(f, p))])
                break
        if len(priority) == 1:
            games += [(priority[0], 1)] # add a bye game
        return games
    
    def _end_of_round(self, tournament):
        with DatabaseManager() as c:
            rounds = (c.execute("""SELECT MAX(round) FROM games WHERE tournamentId = ?""", (tournament,)).fetchone()[0] or 0) + 1
            teamCount = c.execute("SELECT COUNT(*) FROM tournamentTeams WHERE tournamentId = ?;", (tournament,)).fetchone()[0]
            
            maxRound = ceil(log2(teamCount)) + 2 # we will do 1 round above the maximum
            if rounds == 1:
                teams = c.execute(
                    """
                        SELECT 
                            tournamentTeams.teamId, 
                            (IFNULL(e1.elo, 1500) + IFNULL(e2.elo, 0) + IFNULL(e3.elo, 0))/(1 + (e2.elo IS NOT NULL) + (e3.elo IS NOT NULL)) as eloFinal
                        FROM 
                            tournamentTeams
                            LEFT JOIN teams ON teams.id = tournamentTeams.teamId
                            LEFT JOIN (SELECT playerId, SUM(eloChange)+1500 as elo FROM eloChange GROUP BY playerId) AS e1 ON e1.playerId = teams.captain
                            LEFT JOIN (SELECT playerId, SUM(eloChange)+1500 as elo FROM eloChange GROUP BY playerId) AS e2 ON e2.playerId = teams.nonCaptain
                            LEFT JOIN (SELECT playerId, SUM(eloChange)+1500 as elo FROM eloChange GROUP BY playerId) AS e3 ON e3.playerId = teams.substitute
                        WHERE 
                            tournamentTeams.tournamentId = ?
                        GROUP BY 
                            tournamentTeams.teamId
                        ORDER BY 
                            eloFinal DESC;
                            """,(tournament,),
                ).fetchall()
                games = []
                while len(teams) >= 2:
                    games += [(teams.pop(0)[0], teams.pop(-1)[0])]
                if len(teams) == 1:
                    games += [(teams[0][0], 1)] # add a bye game
            elif rounds <= maxRound:
                teams = c.execute("""
                                SELECT Team, sum(games), (sum(wins)*100)/(sum(games)) as resultWinPercentage, sum(elo) as resultElo
                                FROM (
                                    SELECT teamOne as Team, count(teamOne) as games, 0 as wins,0 AS elo
                                        FROM games
                                        WHERE 
                                            tournamentId = ?
                                            AND ended = 1 -- basically to ignore BYE game
                                            AND isFinal = 0
                                            AND teamOne != 1
                                        GROUP BY teamOne
                                    UNION ALL
                                    SELECT teamTwo as Team, count(teamTwo) as games, 0 as wins,0 AS elo
                                        FROM games
                                        WHERE 
                                            tournamentId = ?
                                            AND ended = 1
                                            AND isFinal = 0
                                            AND teamTwo != 1
                                        GROUP BY teamTwo
                                    UNION ALL
                                    SELECT 
                                        tournamentTeams.teamId, 0, 0,
                                        (e1.elo + IFNULL(e2.elo, 0) + IFNULL(e3.elo, 0))/(1 + (e2.elo IS NOT NULL) + (e3.elo IS NOT NULL)) as elo
                                        FROM 
                                            tournamentTeams
                                            LEFT JOIN teams ON teams.id = tournamentTeams.teamId
                                            LEFT JOIN (SELECT playerId, SUM(eloChange)+1500 as elo FROM eloChange GROUP BY playerId) AS e1 ON e1.playerId = teams.captain
                                            LEFT JOIN (SELECT playerId, SUM(eloChange)+1500 as elo FROM eloChange GROUP BY playerId) AS e2 ON e2.playerId = teams.nonCaptain
                                            LEFT JOIN (SELECT playerId, SUM(eloChange)+1500 as elo FROM eloChange GROUP BY playerId) AS e3 ON e3.playerId = teams.substitute
                                        WHERE 
                                            tournamentTeams.tournamentId = ?
                                        GROUP BY 
                                            tournamentTeams.teamId
                                    UNION ALL
                                    SELECT winningTeam as Team, 0 as games, count(winningTeam) as wins, 0 AS elo
                                        FROM games
                                        WHERE 
                                            tournamentId = ?
                                            AND ended = 1
                                            AND isFinal = 0
                                            and isRanked = 1
                                        GROUP BY winningTeam
                                )
                                GROUP BY Team
                                ORDER BY resultWinPercentage DESC, resultElo DESC;""", 
                                (tournament,)*4).fetchall()
                previous_games = c.execute("""SELECT teamOne, teamTwo FROM games WHERE tournamentId = ? AND isFinal = 0 AND ended = 1""", (tournament,)).fetchall()
                games = self.find_bracket(previous_games, teams)
            else:
                c.execute("""UPDATE tournaments SET inFinals = 1 WHERE tournaments.id = ?""", (tournament,))
                return  
            for team1, team2 in games:
                manageGame.create_game(tournament, team1, team2, round_number=rounds)

