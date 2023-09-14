import json

from structure.Team import Team


class Official:
    def __init__(self, name: str, team: Team | None, primary: bool = False):
        self.name: str = name
        self.team: Team | None = team
        self.games_officiated: int = 0
        self.primary: bool = primary

    def __repr__(self):
        first, second = self.name.split(" ")
        first = first[0] + ". "
        return first + second


class Officials:
    def __init__(self, tournament):
        self.officials: list[Official] = []
        self.tournament = tournament
        self.primary: list[Official] = []
        with open("./resources/officials.json") as fp:
            for i in json.load(fp):
                team = ([j for j in self.tournament.teams if j.name == i["team"]] + [None])[0]
                o = Official(i["name"], team)
                if i["primary"]:
                    self.primary.append(o)
                self.officials.append(o)

    def get_primary_officials(self):
        return sorted(self.primary, key=lambda it: it.games_officiated)

    def get_officials(self):
        return sorted(self.officials, key=lambda it: it.games_officiated)
