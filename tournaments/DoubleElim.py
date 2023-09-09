from structure.Fixture import Fixture
from tournaments.Fixtures import Fixtures


class DoubleElim(Fixtures):
    def __init__(self, teams):
        super().__init__(teams)

    def next_round(self) -> [Fixture]:
        # This is where the entire fixtures are generated
        # if you need a fixture to depend on the winner or loser of another
        # then you can use Fixture.winner and Fixture.loser,
        # which are both set up to automatically fill at run time
        # the constructor for Fixture is (teamOne, teamTwo, roundNumber, Tournament)
        # so just pass self as the third param and the number of the round for the fourth.
        # Feel free to look around at the other ones I've implemented.
        return []
