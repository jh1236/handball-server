from structure.Game import Game
from structure.Team import BYE
from tournaments.Fixtures import Fixtures
from collections import defaultdict

class Swiss(Fixtures):
    def __init__(self, tournament, rounds=6):

        self.teams_fixed = tournament.teams.copy()
        if len(self.teams_fixed) % 2 == 1:
            self.teams_fixed.append(BYE)
        self.round_count = rounds
        self.max_rounds = len(self.teams_fixed) - 1

        super().__init__(tournament)

    def generate_round(self):
        """iterator that returns each round, call next value after each round is completed"""
        for i in range(self.round_count+1):
            yield self.match_make(i)
                
            

    def match_make(self, r):
        if len(self.teams_fixed[0].teams_played) + 1 == len(self.teams_fixed):
            raise Exception("All games have been played")
        
        roster = []
        
        unfilled = sorted(self.teams_fixed, key=lambda x: x.points_for-x.points_against)
        unfilled = sorted(unfilled, key=lambda x: x.games_won)
        
        counter = 0
        while unfilled:
            target = unfilled.pop(0)
            
            for i, team in enumerate(unfilled):
                if not target.has_played(team): 
                    roster.append(x := [target, unfilled.pop(i)])
                    break
            else:
                # could not find a unique match, 
                # put them on the end of the array.
                unfilled.append(target)     
                
            counter += 1
            if counter > (len(self.teams_fixed) * 2):
                roster = self.fallback()
                unfilled = False
        
        # turn the proposed games into game objects
        final_roster = []
        for j in roster:
            final_roster.append(Game(j[0], j[1], self))
            
        return final_roster


    def get_possible_pairs(self) :
        possible_pairs = defaultdict(list)
        for j in self.teams_fixed:
            for k in self.teams_fixed:
                if not j.has_played(k) and j != k:
                    possible_pairs[j].append(k)
        return possible_pairs
            
    def fallback(self):
        print("FALL BACK!!!!!!\n"*3)

        possible_pairs = self.get_possible_pairs()
        
        # brute force pairs that are all unique
        used = []
        games = []
        self.find_unique_recursive(games, used, possible_pairs)
        return games
    
    def get_available_teams(self, used, teams=None):
        """
        filters out teams which are already being used, allowing for simpler code and a small amount of
        optimisations"""
        if teams == None:
            teams = self.teams_fixed
        return [team for team in teams if team not in used]
        
    
    def find_unique_recursive(self, games, used, possible_pairs):
        for team in self.get_available_teams(used):
            used.append(team)
            for other_team in self.get_available_teams(used, possible_pairs[team]):
                games.append([team, other_team])
                used.append(other_team)
                if len(used) != len(self.teams_fixed):
                    self.find_unique_recursive(games, used, possible_pairs)
                if len(used) == len(self.teams_fixed):
                    return
                used.pop()
                games.pop()
            used.pop()

            
