from structure import Game, Team
from tournaments.Tournament import Tournament
from util import n_chunks


class PooledMatches(Tournament):
    def __init__(self, teams, pool_count):
        super().__init__(teams)
        teams = teams.copy()
        self.pool_count = 0
        while len(teams) % (2 * pool_count) != 0:
            teams.append(None)
        self.pools = [*n_chunks(teams, pool_count)]
        print(self.pools)

    def __iter__(self):
        self.pool_count = -1
        return super().__iter__()

    def print_ladder(self):
        for i, pool in enumerate(self.pools, start=1):
            print(f"Pool {i}:")
            for j, v in enumerate([k for k in pool if k]):
                print(f"{j}: {v} ({v.wins} wins)")

    def next(self) -> Game | None:
        self.pool_count += 1
        self.pool_count %= len(self.pools)
        team_one = self.pools[self.pool_count][self.count]
        team_two = self.pools[self.pool_count][len(self.pools) - 1 - self.count]
        if not team_one and not team_two:
            return None
        return Game(team_one, team_two)

    def next_round(self):
        out = []
        for i in self.pools:
            out.append([i[0]] + [i[-1]] + i[1:-1])
        self.pools = out

    def rounds(self):
        return len(self.pools[0]) - 1
