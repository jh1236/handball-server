import json
from random import Random
from typing import Callable

from werkzeug.datastructures import MultiDict

from structure.Game import Game
from utils.util import chunks_sized

from utils.databaseManager import DatabaseManager
from collections import defaultdict

with DatabaseManager() as db:
    db.execute("SELECT event,taunt FROM taunts")
    t = db.fetchall()
    taunts = defaultdict(list)
    for key,value in t:
        taunts[key].append(value)
    
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
        "e": ["Forfeit by %t."],
    }
    if not game.started:
        return ["Hang Tight, the game will start soon!"]
    else:
        out.append(
            f"Game Begin! {game.teams[not game.first_team_serves]} will be serving."
        )
    teams = [i.start_players.copy() for i in game.teams]
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
            string = f"{char_to_taunt[c][0][:-1]}, What a shocking call!!"
        elif c == "!":
            if j[1].lower() == "u":
                teams[not j[1].isupper()][0], teams[not j[1].isupper()][1] = (
                    teams[not j[1].isupper()][1],
                    teams[not j[1].isupper()][0],
                )
            continue
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
        out.append(
            f"Game Over! The winner was {game.winner.name}, and best on court was {game.best_player.first_name()}."
        )
    return out


def game_string_to_list(game: Game) -> list[str]:
    if game.bye:
        return ["Bye"]
    rand = Random(game.id)
    out = []
    char_to_taunt = {
        "s": "Score by %p",
        "a": "Ace by %p against %r",
        "g": "Green Card for %p",
        "y": "Yellow Card (3 rounds) for %p",
        "v": "Red Card for %p",
        "t": "Timeout by %t",
        "f": "Fault by %p",
        "x": "%p subbed off for %q",
        "e": "Forfeit by %t",
    }
    if not game.started:
        return ["Hang Tight, the game will start soon!"]
    else:
        out.append(
            f"Game Begin! {game.teams[not game.first_team_serves]} will be serving."
        )
        for i in game.teams:
            out.append(
                f"Starting lineup of {i}: {', '.join(j.name for j in i.start_players)}"
            )
    teams = [i.start_players.copy() for i in game.teams]
    card_count = 0
    first_team_served_before = False
    cards = [0, 0]
    score = [0, 0]
    for j in chunks_sized(game.game_string, 2):
        cards = [i - 1 if i > 0 else i for i in cards]
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
            score[not j[1].isupper()] += 1
            if "null" in other_player.lower():
                other_player = other_players[0].first_name()
        elif c == "s":
            score[not j[1].isupper()] += 1
        elif c == "t":
            player = rand.choice(players).first_name()
        elif c == "x":
            teams[not j[1].isupper()] = game.teams[not j[1].isupper()].players
            team_mate = players[-1].first_name()
        if c == "v":
            if cards[not j[1].isupper()] < 0:
                score[j[1].isupper()] = max(11, score[not j[1].isupper()] + 2)
            elif cards[not j[1].isupper()] > 0:
                score[j[1].isupper()] += cards[not j[1].isupper()]
                cards[not j[1].isupper()] = -1
            else:
                cards[not j[1].isupper()] = -1
            if "null" in players[not first].nice_name():
                continue
        if c.isdigit() or c == "y":
            if c == "y":
                c = "3"
            string = f"Yellow Card ({int(c)} rounds) for %p"
            if int(c) < 3:
                c = int(c) + 10
            card_time = int(c)
            if cards[not j[1].isupper()] < 0:
                score[j[1].isupper()] += card_time
            elif cards[not j[1].isupper()] > 0:
                score[j[1].isupper()] += min(cards[not j[1].isupper()], card_time)
                cards[not j[1].isupper()] = abs(cards[not j[1].isupper()] - card_time)
            else:
                cards[not j[1].isupper()] = card_time
        elif c == "!":
            c2 = j[1].lower()
            if c2 == "h":
                string = "Serving player swapped"
            elif c2 == "u":
                teams[not j[1].isupper()][0], teams[not j[1].isupper()][1] = (
                    teams[not j[1].isupper()][1],
                    teams[not j[1].isupper()][0],
                )
                string = "Players swapped sides on %t"
            elif c2 == "w":
                string = "Team serving switched"
            else:
                string = "Jared has forgotten to encode something"
        else:
            string = char_to_taunt[c]
        if game.best_player and (c in ["g", "y", "v"] or c.isdigit()):
            string += f" for {game.cards[card_count].reason}"
            card_count += 1
        string = string.replace("%p", player).replace("%r", other_player)
        string = (
            string.replace("%t", team.name)
            .replace("%o", other_team.name)
            .replace("%q", team_mate)
        )
        string = string.replace("%u", repr(game.primary_official))
        string += f" ({' - '.join(str(i) for i in score)})"
        out.append(string)
    if game.best_player:
        out.append(
            f"Game Over! Winner: {game.winner.name}, Best on court: {game.best_player.first_name()}"
        )
    return out

def filter_games(games_to_check, args, get_details=False):
    out: list[tuple[Game, set]] = []
    details = MultiDict((k, v) for k, v in args.items(multi=True) if not v.startswith("$"))
    sort = ([k for k, v in args.items(multi=True) if v.startswith("^")] + [None])[0]
    for i in games_to_check:
        if i.bye:
            continue
        failed = False
        players = set([j.nice_name() for j in i.all_players])
        for k, v in args.items(multi=True):
            v = v.strip("$^")
            marked = v[0] == "~"
            v = v.strip("~")
            comparer: Callable
            absolute = len(v) > 1 and v[0] == v[1] or v[0] == "="
            if v.startswith("!"):
                v = v.strip("!")
                comparer = lambda i: float(i) != float(v) if str(v).strip().isnumeric() else str(i) != str(v)
            elif v.startswith(">"):
                v = v.strip(">")
                comparer = lambda i: float(i) > float(v)
            elif v.startswith("<"):
                v = v.strip("<")
                comparer = lambda i: float(i) < float(v)
            elif v == "*":
                comparer = lambda  i: True
            else:
                v = v.strip("=")
                comparer = lambda i:  float(i) == float(v) if str(v).strip().isnumeric() else str(i) == str(v)
            match k:
                case "Count":
                    if not comparer(len(players)):
                        failed = True
                        break
                case _:
                    if absolute and any(not comparer((j.get_game_details()|j.get_stats_detailed())[k]) for j in i.all_players if not marked or j.nice_name() in players):
                        failed = True
                        break
                    current_players = set()
                    for j in i.all_players:
                        if comparer((j.get_game_details()|j.get_stats_detailed())[k]):
                            current_players |= {j.nice_name()}
                    if not current_players:
                        failed = True
                        break
                    if marked:
                        players &= current_players
            if not players:
                failed = True
                break
        if not failed:
            out.append((i, players))
    if sort:
        out.sort(key=lambda a: -max([(i.get_game_details()|i.get_stats_detailed())[sort] for i in a[0].all_players if i.nice_name() in a[1]]))
    if get_details:
        return out, details
    return out

def get_query_descriptor(details):
    if not details:
        return ""
    s = "Games"
    has_marked=False
    for k, v in details.items(multi=True):
        marked = v[0] == "~"
        v = v.strip("~")
        v = v.strip("$")
        comparer: Callable
        absolute = len(v) > 1 and v[0] == v[1] or v[0] == "="
        v = v.strip("=")
        if v.startswith("!"):
            v = v.strip("!")
            if absolute:
                if marked and has_marked:
                    s += f" where no specific players have {v} {k}"
                else:
                    s += f" where no players have {v} {k}"
            else:
                if marked:
                    if has_marked:
                        s += f" where that player does not have {v} {k}"
                    else:
                        s += f" where a specific player does not have {v} {k}"
                else:
                    s += f" where any player does not have {v} {k}"
        elif v.startswith(">"):
            v = v.strip(">")
            if absolute:
                if marked and has_marked:
                    s += f" where all specific players have more than {v} {k}"
                else:
                    s += f" where every player has more than {v} {k}"
            else:
                if marked:
                    if has_marked:
                        s += f" where that player has more than {v} {k}"
                    else:
                        s += f" where a specific player has more than {v} {k}"
                else:
                    s += f" where any player has more than {v} {k}"
        elif v.startswith("<"):
            v = v.strip("<")
            if absolute:
                if marked and has_marked:
                    s += f" where all specific players have less than {v} {k}"
                else:
                    s += f" where every player has less than {v} {k}"
            else:
                if marked:
                    if has_marked:
                        s += f" where that player has less than {v} {k}"
                    else:
                        s += f" where a specific player has less than {v} {k}"
                else:
                    s += f" where any player has less than {v} {k}"
        elif v == "*":
            pass
        else:
            has = f"has {v}"
            if v in ["True", "False"]:
                has = "is" + ("" if  v == "True" else " not")
            if absolute:
                if marked and has_marked:
                    s += f" where all specific players have {v} {k}"
                else:
                    s += f" where every player {has} {k}"
            else:
                if marked:
                    if has_marked:
                        s += f" where that player {has} {k}"
                    else:
                        s += f" where a specific player {has} {k}"
                else:
                    s += f" where any player {has} {k}"
        s += ", and"
        has_marked |= (marked and not absolute)
    return s[:-5]