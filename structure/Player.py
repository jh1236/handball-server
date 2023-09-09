class Player:
    def __init__(self, name: str):
        self.name = name
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.time_on_court: int = 0
        self.time_carded: int = 0

    def __repr__(self):
        return self.name

    def score_goal(self, ace=False):
        pass

    def green_card(self):
        pass

    def yellow_card(self, time: int = 3):
        pass

    def red_card(self):
        pass

    def next_point(self):
        pass

    def game_player(self):
        return GamePlayer(self)


class GamePlayer:
    def __init__(self, player: Player):
        self.player = player
        self.name = self.player.name
        self.card_time_remaining: int = 0  # how many rounds the player is carded for (-1 is infinite)
        self.card_duration: int = 0  # total time the player is carded for (used for progress bar in app)

    def score_point(self, ace: bool):
        if True: return
        # TODO: make it so that stats are added at the end of the game (to allow for undos)
        self.player.score_goal(ace)

    def green_card(self):
        if True: return
        self.player.green_cards += 1

    def yellow_card(self, time):
        # self.player.yellow_cards += 1
        if self.card_time_remaining >= 0:
            self.card_time_remaining += time
            self.card_duration += time

    def red_card(self):
        # self.player.red_cards += 1
        self.card_time_remaining = -1

    def is_carded(self):
        return self.card_time_remaining != 0

    def next_point(self):
        if self.card_time_remaining > 0:
            self.card_time_remaining -= 1

    def reset(self):
        self.card_time_remaining = 0
        self.card_duration = 0
