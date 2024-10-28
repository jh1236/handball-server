from math import log2, ceil
from typing import Iterable

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
    
    def __can_be_played(self, previous_games: set[tuple[Teams, Teams]], team_one: Teams, team_two: Teams):
        if (team_one, team_two) in previous_games or (team_two, team_one) in previous_games:
            return False
        return True
    

    def brute_force(self, previous_games, teams):
        # This is a brute force algorithm that will try to find a bracket that works
        # It will try to find a bracket that works by trying all possible combinations
        games = []
        while len(teams) >= 2:
            logger.warning("Brute forcing a bracket")
            team1 = teams.pop(0)
            for team2 in teams:
                if self.__can_be_played(previous_games, team1, team2):
                    games.append((team1, team2))
                    teams.remove(team2)
                    break
        return games, teams   
    
    def find_bracket(self, previous_games: set[tuple[Teams]], teams: list[Teams]) -> list[tuple[Teams]]:
        # honestly the complexity of sorting doesn't really matter here, just as long as it exists
        priority = teams.copy()
        games = [] 
        print(f"{(Teams.BYE in priority)=}")
        # add bye team if necessary
        if len(priority) % 2 != 0:
            logger.critical("ODD NUMBER OF TEAMS")
            
        while len(priority) >= 2:
            team1 = priority.pop(0)
            found = False
            
            for j in priority:
                if self.__can_be_played(previous_games, team1, j):
                    
                    logger.debug(f"Found a game between {team1.id}:{team1.name} - {team1.games_played(11)} {team1.win_percentage(11)} and {j.id}:{j.name} - {j.games_played(11)} {j.win_percentage(11)}")
                    games.append((team1, j))
                    priority.remove(j)
                    found = True
                    break
                
            if found == False:
                # shit broke, time to brute force :cries:
                games, teams = self.brute_force(previous_games, teams)
                break
        print(games)
        return manage_game.teams_to_id(games)
    
    def _end_of_round(self, tournament):
        with DatabaseManager() as c:
            round = (db.session.query(func.max(Games.round)).filter(Games.tournament_id == tournament).scalar() or 0) + 1

            teams = TournamentTeams.query.filter(TournamentTeams.tournament_id == tournament).all()
            teams = [t.team for t in teams] # get Teams from TournamentTeams
            if len(teams)%2 == 1:
                logger.debug("odd amount of teams, BYE team added")
                teams.append(Teams.BYE)
                
            teams = sorted(teams, key=lambda x: (x.games_played(tournament=tournament), -x.win_percentage(tournament), -x.elo()))
            
            for j in teams:
                print(j.name, j.games_played(tournament=tournament), j.win_percentage(tournament), j.elo())
            
            
            teamCount = len(teams)
            maxRounds = ceil(log2(teamCount)) 
            logger.debug(f"Generating round {round}/{maxRounds} of swiss with {teamCount} teams")
            
            if round == 1:
                games = []
                while teams:
                    games.append((teams.pop(0).id, teams.pop(-1).id))
                    
            elif round <= maxRounds:
                previous_games = Games.query.filter(Games.tournament_id == tournament).all()
                previous_games = {(i.team_one, i.team_two) for i in previous_games}
                    
                games = self.find_bracket(previous_games, teams)
            else:
                Tournaments.query.filter(Tournaments.id == tournament).update({"in_finals": 1})
                db.session.commit()
                return  
            print(games)
            for team1, team2 in games:
                manage_game.create_game(tournament, team1, team2, round_number=round)