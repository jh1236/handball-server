import json
from structure.Team import Team


class Official:
    def __init__(self, name: str, key: str, team: list[Team], primary: bool = False, finals: bool = False,
                 admin=False):
        self.admin = admin
        self.finals: bool = finals
        self.name: str = name
        self._tidy_name: str = None
        self.team: list[Team] = team
        self.internal_games_umpired: int = 0
        self.internal_games_scored: int = 0
        self.games_court_one = 0
        self.key: str = key
        self.primary: bool = primary
        self.games_umpired: int = 0
        self.games_scored: int = 0
        self.faults: int = 0
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.rounds_umpired: int = 0
        self.tournament = None

    def __repr__(self):
        return self.tidy_name()

    def tidy_name(self):
        if self._tidy_name is not None:
            return self._tidy_name
        from structure.AllTournament import get_all_officials
        first, second = self.name.split(" ", 1)
        others = self.tournament.officials if self.tournament else get_all_officials()
        for i in others:
            if i.name == self.name:
                continue
            other_first, other_second =  i.name.split(" ", 1)
            if other_first[0] == first[0] and second == other_second:
                first = first[:2] + ". "
                self._tidy_name = first + second
                return self._tidy_name
        first = first[0] + ". "
        self._tidy_name = first + second
        return self._tidy_name

    def nice_name(self):
        return self.name.lower().replace(" ", "_").replace("'","")


    def get_stats(self):
        return {
            "Green Cards Given": self.green_cards,
            "Yellow Cards Given": self.yellow_cards,
            "Red Cards Given": self.red_cards,
            "Cards Given": self.red_cards + self.yellow_cards + self.green_cards,
            "Cards Per Game": round((self.red_cards + self.yellow_cards + self.green_cards) / (self.games_umpired or 1), 2),
            "Faults Called": self.faults,
            "Faults Per Game": round(self.faults / (self.games_umpired or 1), 2),
            "Games Umpired": self.games_umpired,
            "Games Scored": self.games_scored,
            "Rounds Umpired": self.rounds_umpired,
        }

    def add_stats(self, d):
        self.green_cards += d["Green Cards Given"]
        self.yellow_cards += d["Yellow Cards Given"]
        self.red_cards += d["Red Cards Given"]
        self.faults += d["Faults Called"]
        self.games_umpired += d["Games Umpired"]
        self.games_scored += d["Games Scored"]
        self.rounds_umpired += d["Rounds Umpired"]

    def reset(self):
        self.internal_games_umpired = 0
        self.internal_games_scored = 0
        self.games_court_one = 0
        self.games_umpired = 0
        self.games_scored = 0
        self.faults = 0
        self.green_cards = 0
        self.yellow_cards = 0
        self.red_cards = 0
        self.rounds_umpired = 0


NoOfficial = Official("No one", "", [])


def get_officials(tournament) -> list[Official]:
    officials: list[Official] = []
    names = tournament.details["officials"]
    if names == "signup":
        with open("./config/signups/officials.json", "r+") as fp:
            names = json.load(fp)
    with open("./config/officials.json", "r") as fp:
        for n, v in json.load(fp).items():
            team = [j for j in tournament.teams if n in [k.name for k in j.players]]
            o: Official = Official(n, v["key"], team, primary=v["primary"], finals=v["finals"], admin = v["admin"])
            if tournament.details["officials"] == "all" or n in names:
                officials.append(o)
                o.tournament = tournament
    return sorted(officials, key=lambda it: it.nice_name())
