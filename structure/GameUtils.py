import json
from random import Random

from structure.Game import Game
from util import chunks_sized

with open("./resources/taunts.json") as fp:
    taunts = json.load(fp)


def game_string_to_commentary(game: Game) -> list[str]:
    rand = Random()
    player_names = {
        "L": game.players()[0].tidy_name(),
        "R": game.players()[1].tidy_name(),
        "l": game.players()[2].tidy_name(),
        "r": game.players()[3].tidy_name(),
        "t": "Why do you want to",
        "T": "use this?!?!?"
    }
    out = []
    for j in chunks_sized(game.game_string, 2):
        player = player_names[j[1]]
        team = game.teams[not j[1].isupper()]
        team_mate = [i for i in team.players if i.tidy_name() != player][0].tidy_name()
        other_team = game.teams[j[1].isupper()]
        other_player = other_team.players[rand.randint(0, 1)].tidy_name()
        string = ""
        c = j[0].lower()
        if c == 's':
            string = rand.choice(taunts["score"])
        elif c == 'a':
            serve_receiver = other_team.players[[i.tidy_name() for i in team.players].index(player)].tidy_name()
            string = rand.choice(taunts["ace"]).replace("%a", serve_receiver)
        elif c == 'g':
            string = rand.choice(taunts["green"])
        elif c == 'y':
            string = rand.choice(taunts["yellow"])
        elif c == 'v':
            string = rand.choice(taunts["red"])
        elif c == 't':
            string = rand.choice(taunts["timeout"])
        elif c.isdigit():
            if c == '0':
                string = f"{player} was yellow carded for 10 rounds!"
            else:
                string = f"{player} was yellow carded for {int(c)} rounds!"
        string = (string.replace("%p", player).replace("%r", other_player)
                  .replace("%t", team.name).replace("%o", other_team.name).replace("%q", team_mate))
        out.append(string)
    return out
