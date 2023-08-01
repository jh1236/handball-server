class Team:
    def __init__(self, name):
        self.name = name
        self.wins = 0
        self.games = 0
        self.playedAgainst = []

    def __repr__(self):
        return self.name


class Game:
    def __init__(self, team1, team2):
        self.team1 = self.add(team1, team2)
        self.team2 = self.add(team2, team1)
        self.winner = None

    def team_one_wins(self):
        if self.team1 and self.team2:
            self.team1.wins += 1
            self.winner = self.team1
        else:
            self.winner = self.team1 or self.team2

    def team_two_wins(self):
        if self.team1 and self.team2:
            self.team2.wins += 1
            self.winner = self.team2
        self.winner = self.team1 or self.team2

    def __repr__(self):
        return f"{self.team1 if self.team1 else 'Bye'} vs {self.team2 if self.team2 else 'Bye'}"

    def add(self, team1: Team, team2: Team):
        if team1 is not None:
            team1.games += 1
            if team2 is not None:
                team1.playedAgainst.append(team2)
        return team1
