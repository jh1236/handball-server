from structure.Fixture import Fixture
from tournaments.Tournament import Tournament
from util import n_chunks
from itertools import zip_longest


class PooledMatches(Tournament):
    def __init__(self, teams):
        teams2 = teams.copy()
        self.pool_count = 0
        self.rounds = 0
        while (len(teams2) % 2) != 0:
            teams2.append(None)
        self.pools = [*n_chunks(teams2, 2)]
        for i in self.pools:
            if len(i) % 2 != 0:
                if i[-1]:
                    i.append(None)
                else:
                    del i[-1]
        print(self.pools)
        super().__init__(teams)

    def next_round(self) -> [Fixture]:
        fixtures = []
        for i in range(len(self.pools[0]) // 2):
            mid = len(self.pools[0]) // 2
            for j in range(mid):
                for k in self.pools:
                    if len(k) <= j:
                        continue
                    team_one = k[j]
                    team_two = k[len(k) - 1 - j]
                    match = Fixture(team_one, team_two, i, self)
                    fixtures.append(match)
            # Rotate the teams except the first one
            for k, _ in enumerate(self.pools):
                self.pools[k][1:] = [self.pools[k][-1]] + self.pools[k][1:-1]
        for t1, t2 in zip_longest(*[[j for j in i if j] for i in self.pools]):
            fixtures.append(Fixture(t1, t2, i + 1, self))
        print(fixtures)
        return fixtures
