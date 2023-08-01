from structure import Game
from tournaments.Tournament import Tournament
from util import chunks_sized


class SingleElim(Tournament):
    def __init__(self, teams):
        super().__init__(teams)
        self.games: list[Game] = []

    def __iter__(self):
        self.count = -1
        self.round = 0
        self.games = [Game(i[0], i[1]) for i in chunks_sized(self.teams, 2)]
        return self

    def __next__(self):
        self.count += 1
        self.ranked_teams = sorted(self.teams, key=lambda a: -a.wins)
        if len(self.games) == 1:
            print(f"Standings after round {self.round}")
            for i, v in enumerate(self.ranked_teams):
                print(f"{i}: {v} ({v.wins} wins)")
            raise StopIteration()
        if self.count == len(self.games):
            self.count = 0
            self.round += 1
            self.games = [Game(i[0].winner, i[1].winner) for i in chunks_sized(self.games, 2)]
            print(f"Standings after round {self.round}")
            for i, v in enumerate(self.ranked_teams):
                print(f"{i}: {v} ({v.wins} wins)")
        return self.games[self.count]
