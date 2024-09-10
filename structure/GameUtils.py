from collections import defaultdict
from random import random, Random
from typing import Callable

from sqlalchemy import func
from werkzeug.datastructures import MultiDict

from database import db
from database.models import Games, PlayerGameStats, Taunts, GameEvents
from utils.databaseManager import DatabaseManager


def copy_case(string: str, other: str) -> str:
    if other.isupper():
        return string.upper()
    return string.lower()


def game_string_to_commentary(game: int) -> list[str]:
    out = []
    taunts = defaultdict(list)
    taunts_query = Taunts.query.all()
    for i in taunts_query:
        taunts[i.event].append(i.taunt)
    ge = GameEvents.query.filter(GameEvents.game_id == game).all()

    r = Random(game)

    if not game:
        return ["Hang Tight, the game will start soon!"]
    for i in ge:
        if not i.player: continue
        possible = taunts[i.event_type]
        string = possible[r.randint(0, len(possible) - 1)]
        string = (
            string.replace("%t", i.team.name)
            .replace("%p", i.player.name)
            .replace("%r", i.opposite_player.name)
            .replace("%o", i.other_team.name)
            .replace("%q", i.team_mate.name)
            .replace("%u", repr(i.game.official.person.name))  # this is getting ridiculous...
        )
        out.append(string)
    return out


def game_string_to_events(game: int) -> list[str]:
    out = []
    ge = GameEvents.query.filter(GameEvents.game_id == game).all()
    for i in ge:
        if not i.player: continue
        string = f"{i.event_type} for {i.player.name} from {i.team.name}."
        out.append(string)
    return out


def filter_games(args, get_details=False):
    games = db.session.query(Games).join(PlayerGameStats).filter(Games.is_bye == False, Games.started)
    details = MultiDict((k, v) for k, v in args.items(multi=True) if not v.startswith("$"))
    sort = ([k for k, v in args.items(multi=True) if v.startswith("^")] + [None])[0]
    for k, v in args.items(multi=True):
        v = v.strip("$^")
        marked = v[0] == "~"
        v = v.strip("~")
        comparer: Callable
        absolute = len(v) > 1 and v[0] == v[1] or v[0] == "="
        if v.startswith("!"):
            v = v.strip("!")
            comparer = lambda i: i != float(v) if str(v).strip().isnumeric() else str(i) != str(v)
        elif v.startswith(">"):
            v = v.strip(">")
            comparer = lambda i: i > float(v)
        elif v.startswith("<"):
            v = v.strip("<")
            comparer = lambda i: i < float(v)
        elif v == "*":
            comparer = lambda i: True
        else:
            v = v.strip("=")
            comparer = lambda i: i == float(v)
        match k:
            case _:
                games = games.filter(comparer(PlayerGameStats.row_by_name(k)))

    if sort:
        games.order_by(PlayerGameStats.row_by_name(sort))
    games = games.all()
    games = [(i, PlayerGameStats.query.filter(PlayerGameStats.game_id == i.id).all()) for i in games]
    if get_details:
        return games, details
    return games


def get_query_descriptor(details):
    if not details:
        return ""
    s = "Games"
    has_marked = False
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
                has = "is" + ("" if v == "True" else " not")
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
