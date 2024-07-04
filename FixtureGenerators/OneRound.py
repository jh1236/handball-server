from FixtureGenerators.FixturesGenerator import FixturesGenerator


class OneRound(FixturesGenerator):

    def __init__(self, tournament_id):
        super().__init__(tournament_id, fill_officials=False, editable=True, fill_courts=True)

    def _end_of_round(self, tournament_id):
        pass
