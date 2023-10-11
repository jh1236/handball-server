import json

from structure.Team import Team


class Official:
    def __init__(self, name: str, key: str, team: list[Team], primary: bool = False):
        self.name: str = name
        self.team: list[Team] = team
        self.games_officiated: int = 0
        self.games_court_one = 0
        self.key: str = key
        self.primary: bool = primary
        self.games_umpired = 0
        self.faults: int = 0
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.rounds_umpired: int = 0

    def __repr__(self):
        return self.tidy_name()

    def tidy_name(self):
        first, second = self.name.split(" ")
        first = first[0] + ". "
        return first + second

    def nice_name(self):
        return self.name.lower().replace(" ", "_")

    def get_stats(self):
        return {
            "Green Cards Given": self.green_cards,
            "Yellow Cards Given": self.yellow_cards,
            "Red Cards Given": self.red_cards,
            "Cards Given": self.red_cards + self.yellow_cards + self.green_cards,
            "Faults Called": self.faults,
            "Games Umpired": self.games_umpired,
            "Rounds Umpired": self.rounds_umpired,
        }


NoOfficial = Official("None one", "", None)


def get_officials(tournament) -> list[Official]:
    officials: list[Official] = []
    with open("./config/officials.json", "r") as fp:

        for n, v in json.load(fp).items():
            team = [j for j in tournament.teams if n in [k.name for k in j.players]]
            o = Official(n, v["key"], team)

            if tournament.details["officials"] == "all" or n in tournament.details["officials"]:
                officials.append(o)
    return officials
