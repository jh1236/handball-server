import itertools

from structure.Fixture import Fixture
from structure.Team import BYE
from tournaments.Tournament import Tournament


class Swiss(Tournament):
    def __init__(self, teams, rounds=6):

        self.teams_fixed = teams.copy()
        if len(self.teams_fixed) % 2 == 1:
            self.teams_fixed.append(BYE)
        self.round_count = rounds
        self.max_rounds = len(self.teams_fixed) - 1

        super().__init__(teams)

    def generate_round(self):
        """iterator that returns each round, call next value after each round is completed"""
        for i in range(self.round_count):
            yield self.match_make(i)

    def match_make(self, r):
        """ 
        find the highest scoring team and pair them with the next highest scoring team.
        if a match can't be made, this function will progressively fuck with the players respective rankings
        until a match can be made, this function should produce matches until all possible rounds can be made
        at the cost of your cpu usage, if a case where a match cannot be made it will fall back to having duplicate
        rounds cause fuck you for not using round-robin
        """

        # check if there are any matches remaining, this should never run.
        if len(self.teams_fixed[0].teams_played) + 1 == len(self.teams_fixed):
            raise Exception("all games have been played")

        roster = []
        unfilled = sorted(self.teams_fixed, key=lambda x: x.wins, reverse=True)

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

                if not found:
                    if loop_count > self.max_rounds:  # fallback if alot of
                        return self.fall_back_swiss(target, unfilled, roster)

                    # if a roster can't be made, move the problem player to the end of the array, 
                    # and reverse the array to give more chance

                    loop_count += 1
                    remaining = unfilled
                    unfilled = list(itertools.chain(remaining, *roster, [target]))
                    unfilled.reverse()
                    roster = []
                    trial = False
        print(roster)
        while self.fixtures and (roster[0][0] in self.fixtures[-1] or roster[0][1] in self.fixtures[-1]):
            roster.append(roster.pop(0))

        return [Fixture(team1, team2, r, self) for team1, team2 in roster]

    @staticmethod
    def fall_back_swiss(target, unfilled, roster):
        print("COULD NOT FIND UNIQUE TEAM. ALLOWING REPLAY")
        roster.append([target, unfilled.pop(0)])
        for n in range(0, len(unfilled), 2):
            roster.append(unfilled[n:n + 2])
        print(roster)
        return roster
