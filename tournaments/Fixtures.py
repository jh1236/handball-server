import json

from structure.Game import Game


class Fixtures:
    def __init__(self, tournament):
        self.tournament = tournament
        self.rounds: list[list[Game]] = []
        self.generator = self.generate_round()
        self.get_game(0)  # used to initialise the first round
        self.load()
        self.appoint_umpires()

    def games_to_list(self) -> list[Game]:
        return [game for r in self.rounds for game in r]

    def get_game(self, game_id: int) -> Game:
        while len(self.games_to_list()) <= game_id:
            print("called gen")
            self.rounds.append(next(self.generator))
        if all([i.best_player for i in self.rounds[-1]]):
            self.rounds.append(next(self.generator))
        self.appoint_umpires()
        self.assign_ids()
        return self.games_to_list()[game_id]

    def generate_round(self):
        # Subclass will yield from this func
        raise NotImplementedError()

    def save(self):
        print("Saving...")
        with open("./resources/games.json", "w+") as fp:
            json.dump([[j.as_map() for j in i] for i in self.rounds], fp, indent=4, sort_keys=True)

    def load(self):
        with open("./resources/games.json") as fp:
            rounds = [[Game.from_map(j, self.tournament) for j in i] for i in json.load(fp)]
        for i, r in enumerate(rounds):
            for j, g in enumerate(r):
                self.get_game(g.id)
                self.rounds[i][j] = g
        self.assign_ids()

    def assign_ids(self):
        for i, g in enumerate(self.games_to_list()):
            g.id = i

    def dump(self):
        self.rounds: list[list[Game]] = []
        self.generator = self.generate_round()
        self.get_game(0)  # used to initialise the first round
        self.save()

    def appoint_umpires(self):
        for prev, game, next in zip([None] + self.games_to_list()[:-1], self.games_to_list(),
                                    self.games_to_list()[1:] + [None]):
            if game.primary_official is not None: continue
            teams = [i.team for i in game.teams] + ([] if not next else [i.team for i in next.teams])
            for p in self.tournament.officials.get_primary_officials():
                if prev and prev.primary_official == p: continue
                if p.team and p.team in teams:
                    continue
                print(p.name, p.games_officiated, game)
                game.set_primary_official(p)
                break
