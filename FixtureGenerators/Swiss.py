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
            round = (db.session.query(func.max(Games.round)).filter(Games.tournament_id == tournament).scalar() or 0) + 1
            teamCount = TournamentTeams.query.filter(TournamentTeams.tournament_id == tournament).count()
            
            maxRounds = ceil(log2(teamCount)) 
            
            if round == 1:
                
                teams = db.session.query.filter(TournamentTeams.tournament_id == tournament).all()
                teams = sorted(teams, key=lambda x: -x.team.elo())

                games = []
                while len(teams) >= 2:
                    games += [(teams.pop(0).team_id, teams.pop(-1).team_id)]
                if len(teams) == 1:
                    games += [(teams[0].team_id, 1)] # add a bye game
            elif round <= maxRounds:
                teams = TournamentTeams.query.filter(TournamentTeams.tournament_id == tournament).all()
                teams = sorted(teams, key=lambda x: (-x.team.win_percentage(tournament), -x.team.elo()))
                
                previous_games = Games.query.filter(Games.tournament_id == tournament).all()
                previous_games = {(i.team_one, i.team_two) for i in previous_games}
                    
                games = self.find_bracket(previous_games, teams)
            else:
                Tournaments.query.filter(Tournaments.id == tournament).update({"in_finals": 1})
                db.session.commit()
                return  
            
            for team1, team2 in games:
                manage_game.create_game(tournament, team1, team2, round_number=round)