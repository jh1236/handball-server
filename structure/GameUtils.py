import json
from random import Random

from structure.Game import Game
from utils.util import chunks_sized

with open("./resources/taunts.json") as fp:
    taunts = json.load(fp)


def copy_case(string: str, other: str) -> str:
    if other.isupper(): return string.upper()
    return string.lower()


def game_string_to_commentary(game: Game) -> list[str]:
    if game.bye:
        return [f"Game is bye, {game.teams[0]} wins!"]
    rand = Random(game.id)
    out = []
    char_to_taunt = {
        "s": taunts["score"],
        "a": taunts["ace"],
        "g": taunts["green"],
        "y": taunts["yellow"],
        "v": taunts["red"],
        "t": taunts["timeout"],
        "f": taunts["fault"]
    }
    if not game.started:
        return ["Hang Tight, the game will start soon!"]
    else:
        out.append(f"Game Begin: {game.teams[not game.first_team_serves]} will be serving.")
    for j in chunks_sized(game.game_string, 2):
        first = j[1].upper() == 'L'
        team = game.teams[not j[1].isupper()]
        player = team.players[not first].tidy_name()
        team_mate = [i for i in team.players if i.tidy_name() != player][0].tidy_name()
        other_team = game.teams[j[1].isupper()]
        other_player = rand.choice(other_team.players).tidy_name()
        c = j[0].lower()

        if c == 'a':
            other_player = other_team.players[[i.tidy_name() for i in team.players].index(player)].tidy_name()
        elif c == 't':
            player = rand.choice(team.players).tidy_name()
        if c.isdigit():
            if c == '0':
                string = f"{player} was yellow carded for 10 rounds!"
            else:
                string = f"{player} was yellow carded for {int(c)} rounds!"
        elif (game.primary_official.name == "Aimee Soudure" and rand.randint(0, 15) == 0 and
              c not in ['t', 'a', 's', 'f']):
            string = char_to_taunt[c][0][:-1] + ", What a shocking call!!"
        else:
            string = rand.choice(char_to_taunt[c])
        string = string.replace("%p", player).replace("%r", other_player)
        string = string.replace("%t", team.name).replace("%o", other_team.name).replace("%q", team_mate)
        string = string.replace("%u", repr(game.primary_official))
        out.append(string)
    return out
