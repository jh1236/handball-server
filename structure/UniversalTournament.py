from structure.AllTournament import get_all_teams, get_all_players, get_all_officials


class UniversalTournament:
    def __init__(self):
        self.details = {
            "scorer": True,
        }
    @property
    def teams(self):
        return get_all_teams()

    @property
    def officials(self):
        return get_all_officials()

    @property
    def players(self):
        return get_all_players()

    @staticmethod
    def games_to_list():
        from start import comps

        out = []
        for j in comps.values():
            out += j.games_to_list()
        return out

    @property
    def fixtures(self):
        from start import comps

        out = []
        for j in comps.values():
            out += j.fixtures
        return out

    def nice_name(self):
        return "all_tournaments"

    def get_game(self, id):
        return self.games_to_list()[id]

    def ladder(self):
        return sorted(
            [j for j in self.teams if "bye" not in j.nice_name()],
            key=lambda a: (
                -a.percentage,
                -a.point_difference,
                -a.get_stats()["Points For"],
                -a.get_stats()["Games Won"],
                a.cards,
                a.get_stats()["Red Cards"],
                a.get_stats()["Yellow Cards"],
                a.get_stats()["Faults"],
                a.get_stats()["Timeouts Called"],
                a.nice_name(),
            ),
        )
