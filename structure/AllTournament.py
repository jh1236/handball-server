from structure.Game import Game
from structure.OfficiatingBody import Official
from structure.Player import Player
from structure.Team import Team



def get_all_games() -> list[Game]:
    from start import comps

    return [
        game
        for r in sorted(comps.values(), key=lambda it: it.details["sort"])
        for game in r.games_to_list()
    ]


def get_all_teams() -> list[Team]:
    from start import comps

    teams: dict[str, Team] = {}
    for i in sorted(comps.values(), key=lambda it: it.details["sort"]):
        for t in i.teams:
            if t.name not in teams:
                teams[t.name] = Team(
                    t.name,
                    [Player(j.name) for j in t.players],
                )
    return list(teams.values())


def get_all_players() -> list[Player]:
    from start import comps

    players = {}
    for i in sorted(comps.values(), key=lambda it: it.details["sort"]):
        for t in i.teams:
            for p in t.players:
                if p.name not in players:
                    players[p.name] = [Player(p.name), []]
                if t.name not in [i.name for i in players[p.name][1]]:
                    players[p.name][1].insert(0, t)
    output = []
    for i in sorted(players.values(), key=lambda it: it[0].nice_name()):
        i[0]._team = ([k for k in i[1] if k.has_photo] + [i[1][0]])[0]
        output.append(i[0])
    return output


def get_all_officials() -> list[Official]:
    from start import comps

    officials = {}
    for i in sorted(comps.values(), key=lambda it: it.details["sort"]):
        for j in i.officials:
            if j.nice_name() not in officials:
                officials[j.nice_name()] = Official(j.name, j.key, [], admin=j.admin)
            officials[j.nice_name()].add_stats(j.get_stats())
            officials[j.nice_name()].team += [i for i in j.team if i.nice_name() not in [k.nice_name() for k in officials[j.nice_name()].team]]
    return list(officials.values())
