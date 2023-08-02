from structure.Fixture import Fixture
from tournaments.Tournament import Tournament
from util import n_chunks


class PooledMatches(Tournament):
    def __init__(self, teams, pool_count=2):
        teams = teams.copy()
        self.pool_count = 0
        while (len(teams) % 2) % pool_count != 0:
            teams.append(None)
        self.pools = [*n_chunks(teams, pool_count)]
        print(self.pools)
        super().__init__(teams)

    def generate_fixtures(self) -> [Fixture]:
        fixtures = []
        for i, _ in enumerate(self.pools[0]):
            mid = len(self.pools[0]) // 2
            for j in range(mid):
                for k in self.pools:
                    team_one = k[j]
                    team_two = k[len(self.pools[0]) - 1 - j]
                    match = Fixture(team_one, team_two, self, i)
                    fixtures.append(match)
            # Rotate the teams except the first one
            for k, _ in enumerate(self.pools):
                self.pools[k][1:] = [self.pools[k][-1]] + self.pools[k][1:-1]
        print(fixtures)
        return fixtures
