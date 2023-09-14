import json
from random import Random

from structure.Game import Game
from util import chunks_sized

with open("./resources/taunts.json") as fp:
    taunts = json.load(fp)


def copy_case(string: str, other: str) -> str:
    if other.isupper(): return string.upper()
    return string.lower()


def game_string_to_commentary(game: Game) -> list[str]:
    rand = Random(game.id)
    player_names = {
        "L": game.players()[0].tidy_name(),
        "R": game.players()[1].tidy_name(),
        "l": game.players()[2].tidy_name(),
        "r": game.players()[3].tidy_name(),
        "t": "Why do you want to",
        "T": "use this?!?!?"
    }
    cards = {
        "L": 0,
        "R": 0,
        "l": 0,
        "r": 0,
        "t": 0,
        "T": 0
    }
    out = []
    if not game.game_string:
        return ["Hang Tight, the game will start soon!"]
    for j in chunks_sized(game.game_string, 2):
        player = player_names[j[1]]
        team = game.teams[not j[1].isupper()]
        team_mate = [i for i in team.players if i.tidy_name() != player][0].tidy_name()
        other_team = game.teams[j[1].isupper()]
        other_player = rand.choice(other_team.players).tidy_name()
        string = ""
        if not cards[j[1]]:
            player = team_mate
        if not cards[copy_case("l", j[1]).swapcase()]:
            other_player = other_team.players[1].tidy_name()
        elif not cards[copy_case("r", j[1]).swapcase()]:
            other_player = other_team.players[0].tidy_name()
        c = j[0].lower()
        if c == 's':
            string = rand.choice(taunts["score"])
        elif c == 'a':
            other_player = other_team.players[[i.tidy_name() for i in team.players].index(player)].tidy_name()
            string = rand.choice(taunts["ace"] * 2 + taunts["score"])
        elif c == 'g':
            string = rand.choice(taunts["green"])
        elif c == 'y':
            string = rand.choice(taunts["yellow"])
            if cards[j[1]] >= 0:
                cards[j[1]] += 3
        elif c == 'v':
            string = rand.choice(taunts["red"])
            cards[j[1]] = -1
        elif c == 't':
            player = rand.choice(team.players).tidy_name()
            string = rand.choice(taunts["timeout"])
        elif c == 'f':
            string = rand.choice(taunts["fault"])
        elif c.isdigit():
            if c == '0':
                string = f"{player} was yellow carded for 10 rounds!"
            else:
                string = f"{player} was yellow carded for {int(c)} rounds!"
        string = (string.replace("%p", player).replace("%r", other_player)
                  .replace("%t", team.name).replace("%o", other_team.name).replace("%q", team_mate))
        if game.primary_official.name == "Aimee Soudure" and rand.randint(0, 15) == 0 and c not in ['t', 'a', 's']:
            string = string[:-1]
            string += ", What a shocking call!!"
        out.append(string)
    return out
