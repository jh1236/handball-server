from math import log2, ceil

from FixtureGenerators.FixturesGenerator import FixturesGenerator
from structure import manage_game
from utils.databaseManager import DatabaseManager
from utils.logging_handler import logger
from database import db

from sqlalchemy.sql import func
from sqlalchemy import Integer
from database.models import Games, TournamentTeams, People, Teams, Tournaments, EloChange

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
                    logger.debug(team2)
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
            round = (Games.query.filter(Games.tournament_id == tournament).order_by(Games.round.desc).first() or 0) + 1
            teamCount = TournamentTeams.query.filter(TournamentTeams.tournament_id == tournament).count()
            
            maxRounds = ceil(log2(teamCount)) 
            if round == 1:
                
                # THERE HAS TO BE A NICE WAY TO DO THIS, THIS LOOKS FUCKING UGLY
                elo_subquery1 = (
                    db.session.query(
                        db.column('player_id'),
                        (func.sum(db.column('elo_delta')) + 1500).label('elo')
                    ).group_by(db.column('player_id')).subquery()
                )

                elo_subquery2 = (
                    db.session.query(
                        db.column('player_id'),
                        (func.sum(db.column('elo_delta')) + 1500).label('elo')
                    ).group_by(db.column('player_id')).subquery()
                )

                elo_subquery3 = (
                    db.session.query(
                        db.column('player_id'),
                        (func.sum(db.column('elo_delta')) + 1500).label('elo')
                    ).group_by(db.column('player_id')).subquery()
                )

                teams = (
                    db.session.query(
                        TournamentTeams.team_id,
                        (
                            (
                                # get elo of all players in the team
                                func.coalesce(elo_subquery1.c.elo, 1500) +
                                func.coalesce(elo_subquery2.c.elo, 0) +
                                func.coalesce(elo_subquery3.c.elo, 0)) 
                                / 
                                # divide by the amount of players in the team
                            (
                                1 + 
                                (elo_subquery2.c.elo.isnot(None).cast(Integer)) +
                                (elo_subquery3.c.elo.isnot(None).cast(Integer)))
                        ).label('teamElo')
                    )
                    .join(Teams, Teams.id == TournamentTeams.team_id)
                    .outerjoin(elo_subquery1, elo_subquery1.c.player_id == Teams.captain_id)
                    .outerjoin(elo_subquery2, elo_subquery2.c.player_id == Teams.non_captain_id)
                    .outerjoin(elo_subquery3, elo_subquery3.c.player_id == Teams.substitute_id)
                    .filter(TournamentTeams.tournament_id == tournament)
                    .group_by(TournamentTeams.team_id)
                    .order_by(func.desc('teamElo'))
                    .all()
                )

                games = []
                while len(teams) >= 2:
                    games += [(teams.pop(0)[0], teams.pop(-1)[0])]
                if len(teams) == 1:
                    games += [(teams[0][0], 1)] # add a bye game
            elif round <= maxRounds:
                teams = c.execute("""
                                SELECT Team, sum(games), (sum(wins)*100)/(sum(games)) as resultWinPercentage, sum(elo) as resultElo
                                FROM (
                                    SELECT team_one_id as Team, count(team_one_id) as games, 0 as wins,0 AS elo
                                        FROM games
                                        WHERE 
                                            tournament_id = ?
                                            AND ended = 1 -- basically to ignore BYE game
                                            AND is_final = 0
                                            AND team_one_id != 1
                                        GROUP BY team_one_id
                                    UNION ALL
                                    SELECT team_two_id as Team, count(team_two_id) as games, 0 as wins,0 AS elo
                                        FROM games
                                        WHERE 
                                            tournament_id = ?
                                            AND ended = 1
                                            AND is_final = 0
                                            AND team_two_id != 1
                                        GROUP BY team_two_id
                                    UNION ALL
                                    SELECT 
                                        tournamentTeams.team_id, 0, 0,
                                        (e1.elo + IFNULL(e2.elo, 0) + IFNULL(e3.elo, 0))/(1 + (e2.elo IS NOT NULL) + (e3.elo IS NOT NULL)) as elo
                                        FROM 
                                            tournamentTeams
                                            LEFT JOIN teams ON teams.id = tournamentTeams.team_id
                                            LEFT JOIN (SELECT player_id, SUM(elo_delta)+1500 as elo FROM eloChange GROUP BY player_id) AS e1 ON e1.player_id = teams.captain_id
                                            LEFT JOIN (SELECT player_id, SUM(elo_delta)+1500 as elo FROM eloChange GROUP BY player_id) AS e2 ON e2.player_id = teams.non_captain_id
                                            LEFT JOIN (SELECT player_id, SUM(elo_delta)+1500 as elo FROM eloChange GROUP BY player_id) AS e3 ON e3.player_id = teams.substitute_id
                                        WHERE 
                                            tournamentTeams.tournament_id = ?
                                        GROUP BY 
                                            tournamentTeams.team_id
                                    UNION ALL
                                    SELECT winningTeam as Team, 0 as games, count(winningTeam) as wins, 0 AS elo
                                        FROM games
                                        WHERE 
                                            tournament_id = ?
                                            AND ended = 1
                                            AND is_final = 0
                                            and isRanked = 1
                                        GROUP BY winningTeam
                                )
                                GROUP BY Team
                                ORDER BY resultWinPercentage DESC, resultElo DESC;""", 
                                (tournament,)*4).fetchall()
                
                previous_games = Games.query(Games.team_one_id, Games.team_two_id).filter(Games.tournament_id == tournament, Games.is_final == 0, Games.ended == 1).all()
                games = self.find_bracket(previous_games, teams)
            else:
                Tournaments.query.filter(Tournaments.id == tournament).update({"in_finals": 1})
                db.session.commit()
                return  
            for team1, team2 in games:
                manage_game.create_game(tournament, team1, team2, round_number=round)

