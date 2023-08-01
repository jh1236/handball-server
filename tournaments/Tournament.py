from structure import Game, Team


class Tournament:
    def __init__(self, teams):
        self.teams: list[Team] = teams
        self.ranked_teams: list[Team] = teams
        self.match_count = 0

    def rounds(self):
        raise NotImplemented()

    def __iter__(self):
        self.count = -1
        self.match_count = 0
        self.round = 0
        return self

    def __next__(self):
        self.count += 1
        if self.count >= len(self.teams) // 2:
            self.round += 1
            self.count = 0
            self.ranked_teams = sorted(self.teams, key=lambda a: -a.wins)
            self.next_round()
            print(f"Standings after round {self.round}")
            self.print_ladder()
        if self.round >= self.rounds():
            raise StopIteration()
        self.match_count += 1
        next_element = self.next()
        if not next_element:
            return self.__next__()
        return next_element

    def print_ladder(self):
        for i, v in enumerate([i for i in self.ranked_teams if i]):
            print(f"{i}: {v} ({v.wins} wins)")

    def next(self) -> Game:
        raise NotImplemented("")

    def next_round(self):
        raise NotImplemented("")
