import json
from random import Random

from structure.Game import Game
from utils.util import chunks_sized

with open("./resources/taunts.json") as fp:
    taunts = json.load(fp)


def copy_case(string: str, other: str) -> str:
    if other.isupper():
        return string.upper()
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
        "f": taunts["fault"],
        "x": taunts["sub"],
        'e': ["Forfeit by %t."]
    }
    if not game.started:
        return ["Hang Tight, the game will start soon!"]
    else:
        out.append(
            f"Game Begin! {game.teams[not game.first_team_serves]} will be serving."
        )
    teams = [i.start_players for i in game.teams]
    for j in chunks_sized(game.game_string, 2):
        first = j[1].upper() == "L"
        players = teams[not j[1].isupper()]
        team = game.teams[not j[1].isupper()]
        player = players[not first].first_name()
        if "null" in players[not first].nice_name():
            player = players[first].first_name()
        team_mate = [i for i in players if i.first_name() != player][0].first_name()
        other_team = game.teams[j[1].isupper()]
        other_players = teams[j[1].isupper()]
        other_player = rand.choice(other_players[:2]).first_name()
        if "null" in other_player.lower():
            other_player = other_players[0].first_name()
        c = j[0].lower()

        if c == "a":
            other_player = other_players[
                [i.first_name() for i in players].index(player)
            ].first_name()
            if "null" in other_player.lower():
                other_player = other_players[0].first_name()
        elif c == "t":
            player = rand.choice(players).first_name()
        elif c == "x":
            teams[not j[1].isupper()] = game.teams[not j[1].isupper()].players
            team_mate = players[-1].first_name()
        if c == "v" and "null" in players[not first].nice_name():
            continue
        if c.isdigit():
            if int(c) < 3:
                c = int(c) + 10
            string = f"{player} was yellow carded for {int(c)} rounds!"
        elif (
            game.primary_official.name == "Aimee Soudure"
            and rand.randint(0, 15) == 0
            and c not in ["t", "a", "s", "f"]
        ):
            string = char_to_taunt[c][0][:-1] + ", What a shocking call!!"

        else:
            string = rand.choice(char_to_taunt[c])
        string = string.replace("%p", player).replace("%r", other_player)
        string = (
            string.replace("%t", team.name)
            .replace("%o", other_team.name)
            .replace("%q", team_mate)
        )
        string = string.replace("%u", repr(game.primary_official))
        out.append(string)
    if game.best_player:
        out.append(f"Game Over! The winner was {game.winner().name}, and best on court was {game.best_player.first_name()}.")
    return out
