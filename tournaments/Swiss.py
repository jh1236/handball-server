from structure.Fixture import Fixture
from tournaments.Tournament import Tournament
from structure.Team import Team
import itertools
from structure.Team import BYE

class Swiss(Tournament):
    def __init__(self, teams, rounds=3):
        
        if len(teams)%2 == 1:
            teams.append(BYE)

        self.rounds=rounds
        self.max_rounds = len(teams)-1
        
        super().__init__(teams)
        
    def generate_round(self):
        """itterator that returns each round, call next value after each round is completed"""
        for round in range(self.rounds):
            yield self.matchmake(round)


    def matchmake(self, round):
        """ 
        find the highest scoring team and pair them with the next highest scoring team.
        if a match can't be made, this function will progressivly fuck with the players respective rankings
        until a match can be made, this function should produce matches untill all possible rounds can be made
        at the cost of your cpu usage, if a case where a match cannot be made it will fallback to having duplicate 
        rounds cause fuck you for not using round-robin
        """
        
        # check if there are any matches remaining, this should never run.
        if len(self.teams[0].teams_played) + 1 == len(self.teams):
            raise Exception("all games have been played")
        
        roster = []
        unfilled = sorted(self.teams, key = lambda x: x.wins, reverse=True)

        loop_count = 0 
        while unfilled:
            trial = True
            while len(unfilled) > 0 and trial:

                # grab the highest ranking player
                target = unfilled.pop(0)
                found = False
                # find the next highest ranking player on this list they they have-not
                # played against
                for i, team in enumerate(unfilled):
                    if not target.has_played(team):
                        roster.append([target, team])
                        unfilled.pop(i)
                        found = True
                        break

                if found == False:
                    if loop_count > self.max_rounds: # fallback if alot of 
                        return self.fall_back_Swiss(target, unfilled, roster)
                    
                    # if a roster can't be made, move the problem player to the end of the array, 
                    # and reverse the array to give more chance

                    loop_count += 1 
                    remaining = unfilled
                    unfilled = list(itertools.chain(remaining,*roster,[target]))
                    unfilled.reverse()
                    roster = []
                    trial = False
        return [Fixture(team1, team2, round, self) for team1, team2 in roster] 
            

    def fall_back_Swiss(self, target, unfilled, roster):
        print("COULD NOT FIND UNIQUE TEAM. ALLOWING REPLAY")
        roster.append([target, unfilled.pop(0)])
        for n in range(0, len(unfilled), 2):
            roster.append(unfilled[n:n+2])
        print(roster)
        return roster