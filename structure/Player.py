import json


class Player:
    @classmethod
    def from_map(cls, map):
        player = Player(map["name"])
        player.aces = Player(map["aces"])
        player.goalsScored = Player(map["goalsScored"])
        player.greenCards = Player(map["greenCards"])
        player.yellowCards = Player(map["yellowCards"])
        player.redCards = Player(map["redCards"])
        player.roundsPlayed = Player(map["roundsPlayed"])
        player.roundsCarded = Player(map["roundsCarded"])

    def __init__(self, name: str):
        self.name = name
        self.aces = 0
        self.goalsScored = 0
        self.greenCards = 0
        self.yellowCards = 0
        self.redCards = 0
        self.roundsPlayed = 0
        self.roundsCarded = 0

    def as_str(self):
        return json.dumps(self)
