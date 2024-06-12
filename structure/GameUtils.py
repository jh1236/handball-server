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
    for key, value in t:
        taunts[key].append(value)


def copy_case(string: str, other: str) -> str:
    if other.isupper():
        return string.upper()
    return string.lower()


def game_string_to_commentary(game: int) -> list[str]:
    out = []
    with DatabaseManager() as c:
        game_events = c.execute("""SELECT
       (SELECT taunt FROM taunts WHERE eventType = taunts.event ORDER BY random()) as taunt,
       people.name                                                                 as person,
       t1.name                                                                     as team,
       (SELECT people.name
        FROM teams
                 INNER JOIN playerGameStats ON teams.id = playerGameStats.teamId AND games.id = playerGameStats.gameId
                 INNER JOIN people ON playerGameStats.playerId = people.id
        WHERE (teamOneLeft = people.id OR teamOneRight = people.id OR teamTwoLeft = people.id OR teamTwoRight = people.id) 
          AND people.id <> gameEvents.playerId
          AND teams.id = t1.id)                                                    as team_mate,
       (SELECT people.name
        FROM teams
                 INNER JOIN playerGameStats ON playerGameStats.teamId = teams.id
                 INNER JOIN people ON playerGameStats.playerId = people.id
            AND (eventType <> 'Ace' OR (gameEvents.sideServed = 'Left') = (people.id = gameEvents.teamOneLeft OR people.id = gameEvents.teamTwoLeft))
        WHERE teams.id = t2.id
        ORDER BY random())                                                         as other_player,
       t2.name                                                                     as other_team,
       off.name                                                                    as umpire

FROM gameEvents
         INNER JOIN people on people.id = gameEvents.playerId
         INNER JOIN teams t1 on gameEvents.teamId = t1.id
         INNER JOIN games on gameEvents.gameId = games.id
         INNER JOIN officials on officials.id = games.official
         INNER JOIN people off on off.id = officials.personId
         INNER JOIN teams t2 on (games.teamTwo + games.teamOne - t1.id) = t2.id

WHERE games.id = ?
GROUP BY gameEvents.id""", (game,)).fetchall()
    if not game:
        return ["Hang Tight, the game will start soon!"]
    for taunt, player, team, team_mate, other_player, other_team, umpire in game_events:
        string = taunt.replace("%p", player).replace("%r", other_player)
        string = (
            string.replace("%t", team)
            .replace("%o", other_team)
            .replace("%q", team_mate)
            .replace("%u", repr(umpire))
        )
        out.append(string)
    return out


def game_string_to_events(game: int) -> list[str]:
    out = []
    with DatabaseManager() as c:
        game_events = c.execute("""SELECT
       eventType as taunt,
       people.name                                                                 as person,
       t1.name                                                                     as team,
       (SELECT people.name
        FROM teams
                 INNER JOIN playerGameStats ON teams.id = playerGameStats.teamId AND games.id = playerGameStats.gameId
                 INNER JOIN people ON playerGameStats.playerId = people.id
        WHERE (teamOneLeft = people.id OR teamOneRight = people.id OR teamTwoLeft = people.id OR teamTwoRight = people.id) 
          AND people.id <> gameEvents.playerId
          AND teams.id = t1.id)                                                    as team_mate,
       (SELECT people.name
        FROM teams
                 INNER JOIN playerGameStats ON playerGameStats.teamId = teams.id
                 INNER JOIN people ON playerGameStats.playerId = people.id
            AND (eventType <> 'Ace' OR (gameEvents.sideServed = 'Left') = (people.id = gameEvents.teamOneLeft OR people.id = gameEvents.teamTwoLeft))
        WHERE teams.id = t2.id
        ORDER BY random())                                                         as other_player,
       t2.name                                                                     as other_team,
       off.name                                                                    as umpire

FROM gameEvents
         LEFT JOIN people on people.id = gameEvents.playerId
         LEFT JOIN teams t1 on gameEvents.teamId = t1.id
         INNER JOIN games on gameEvents.gameId = games.id
         LEFT JOIN officials on officials.id = games.official
         LEFT JOIN people off on off.id = officials.personId
         LEFT JOIN teams t2 on (games.teamTwo + games.teamOne - t1.id) = t2.id

WHERE games.id = ? AND (gameEvents.notes is null OR gameEvents.notes != 'Penalty')
GROUP BY gameEvents.id""", (game,)).fetchall()
    for taunt, player, team, team_mate, other_player, other_team, umpire in game_events:
        string = f"{taunt} by {player} from ({team})."
        out.append(string)
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
                comparer = lambda i: True
            else:
                v = v.strip("=")
                comparer = lambda i: float(i) == float(v) if str(v).strip().isnumeric() else str(i) == str(v)
            match k:
                case "Count":
                    if not comparer(len(players)):
                        failed = True
                        break
                case _:
                    if absolute and any(
                            not comparer((j.get_game_details() | j.get_stats_detailed())[k]) for j in i.all_players if
                            not marked or j.nice_name() in players):
                        failed = True
                        break
                    current_players = set()
                    for j in i.all_players:
                        if comparer((j.get_game_details() | j.get_stats_detailed())[k]):
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
        out.sort(key=lambda a: -max(
            [(i.get_game_details() | i.get_stats_detailed())[sort] for i in a[0].all_players if i.nice_name() in a[1]]))
    if get_details:
        return out, details
    return out


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
