import json

from structure.Player import Player


class Team:
    def __init__(self, name: str, left: Player, right: Player):
        self.name = name
        self.leftPlayer = left
        self.rightPlayer = right
        self.played = 0
        self.wins = 0
        self.losses = 0
        self.cards = 0

    def as_str(self):
        return json.dumps(self)