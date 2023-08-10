from structure.Game import Game


class Player:
    @classmethod
    def from_map(cls, map):
        if isinstance(map, str):
            return Player(map)
        player = Player(map["name"])
        player.aces = map["aces"]
        player.goals = map["goals"]
        player.greenCards = map["greenCards"]
        player.yellowCards = map["yellowCards"]
        player.redCards = map["redCards"]
        player.roundsPlayed = map["roundsPlayed"]
        player.roundsCarded = map["roundsCarded"]
        return player

    def __init__(self, name: str):
        self.carded = False
        self.name = name
        self.aces = 0
        self.goals = 0
        self.greenCards = 0
        self.yellowCards = 0
        self.redCards = 0
        self.roundsPlayed = 0
        self.roundsCarded = 0

    def score_goal(self, ace=False):
        if Game.record_stats:
            self.goals += 1
            if ace:
                self.aces += 1

    def green_card(self):
        if Game.record_stats:
            self.greenCards += 1

    def yellow_card(self):
        self.carded = True
        if Game.record_stats:
            self.yellowCards += 1

    def red_card(self):
        self.carded = True
        if Game.record_stats:
            self.redCards += 1

    def next_point(self):
        if Game.record_stats:
            if self.carded:
                self.roundsCarded += 1
            self.roundsPlayed += 1

    def as_map(self):
        dct = {
            "name": self.name,
            "aces": self.aces,
            "goals": self.goals,
            "greenCards": self.greenCards,
            "yellowCards": self.yellowCards,
            "redCards": self.redCards,
            "roundsPlayed": self.roundsPlayed,
            "roundsCarded": self.roundsCarded,
        }
        return dct
