class Card:
    def __init__(self, player, duration: int, reason: str = "Not Provided"):
        self.player = player
        self.duration: int = duration
        self.reason: str = reason

    @property
    def color(self):
        if self.duration > 0:
            return "Yellow"
        if self.duration < 0:
            return "Red"
        return "Green"

    @property
    def sort_key(self):
        if self.duration < 0:
            return 13
        else:
            return self.duration

    @property
    def hex(self):
        if self.duration > 0:
            return "#c96500"
        if self.duration < 0:
            return "#EC4A4A"
        else:
            return "#84AA63"

    def __repr__(self):
        return f"{self.color} card for {self.player}"
