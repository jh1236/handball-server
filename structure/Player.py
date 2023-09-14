class Player:
    def __init__(self, name: str):
        self.tournament = None
        self.name = name
        self.points_scored: int = 0
        self.aces_scored: int = 0
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.votes: int = 0
        self.red_cards: int = 0
        self.time_on_court: int = 0
        self.time_carded: int = 0
        self.rounds_played: int = 0
        self.rounds_carded: int = 0

    def __repr__(self):
        return self.name

    def get_stats(self):
        game_teams: list[GamePlayer] = []
        for i in self.tournament.fixtures.games_to_list():
            player_names = [j.name for j in i.players()]
            if i.in_progress() and self.name in player_names:
                game_teams.append(i.players()[player_names.index(self.name)])

        points_scored = self.points_scored + sum([i.points_scored for i in game_teams])
        aces_scored = self.aces_scored + sum([i.aces_scored for i in game_teams])
        green_cards = self.green_cards + sum([i.green_cards for i in game_teams])
        yellow_cards = self.yellow_cards + sum([i.yellow_cards for i in game_teams])
        red_cards = self.red_cards + sum([i.red_cards for i in game_teams])
        time_on_court = self.time_on_court + sum([i.time_on_court for i in game_teams])
        time_carded = self.time_carded + sum([i.time_carded for i in game_teams])
        return {
            "B&F Votes": self.votes,
            "Points scored": points_scored,
            "Aces scored": aces_scored,
            "Green cards": green_cards,
            "Yellow cards": yellow_cards,
            "Red cards": red_cards,
            "Time on court": f"{time_on_court} rounds",
            "Time Carded": f"{time_carded} rounds",
        }

    def game_player(self):
        return GamePlayer(self)


class GamePlayer:
    def __init__(self, player: Player):
        self.player: Player = player
        self.name = self.player.name
        self.points_scored: int = 0
        self.aces_scored: int = 0
        self.time_on_court: int = 0
        self.time_carded: int = 0
        self.green_cards: int = 0
        self.yellow_cards: int = 0
        self.red_cards: int = 0
        self.card_time_remaining: int = 0  # how many rounds the player is carded for (-1 is infinite)
        self.card_duration: int = 0  # total time the player is carded for (used for progress bar in app)
        self.best: bool = False

    def score_point(self, ace: bool):
        if ace:
            self.aces_scored += 1
        self.points_scored += 1

    def best_player(self):
        self.best = True

    def green_card(self):
        self.green_cards += 1

    def yellow_card(self, time):
        self.yellow_cards += 1
        if self.card_time_remaining >= 0:
            self.card_time_remaining += time
            self.card_duration += time

    def red_card(self):
        self.red_cards += 1
        self.card_time_remaining = -1

    def is_carded(self):
        return self.card_time_remaining != 0

    def next_point(self):
        if self.is_carded():
            self.time_carded += 1
        else:
            self.time_on_court += 1
        if self.card_time_remaining > 0:
            self.card_time_remaining -= 1

    def reset(self):
        self.card_time_remaining = 0
        self.card_duration = 0
        self.points_scored = 0
        self.aces_scored = 0
        self.time_on_court = 0
        self.time_carded = 0
        self.green_cards = 0
        self.yellow_cards = 0
        self.red_cards = 0

    def end(self):
        self.player.points_scored += self.points_scored
        self.player.aces_scored += self.aces_scored
        self.player.time_on_court += self.time_on_court
        self.player.time_carded += self.time_carded
        self.player.green_cards += self.green_cards
        self.player.yellow_cards += self.yellow_cards
        self.player.red_cards += self.red_cards
        self.player.votes += self.best
