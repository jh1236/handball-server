from structure.Game import Game
from structure.OfficiatingBody import Official
from structure.Player import Player
from structure.Team import Team
from structure.Tournament import Tournament

null_tournament = Tournament("-")


def get_all_games(comps: dict[str, Tournament]) -> list[Game]:
    return [game for r in comps.values() for game in r.games_to_list()]


def get_all_teams(comps: dict[str, Tournament]) -> list[Team]:
    teams: dict[str, Team] = {}
    for i in comps.values():
        for t in i.teams:
            if t.name not in teams:
                teams[t.name] = Team(t.name, [Player(j.name) for j in t.players])
                for p, p1 in zip(teams[t.name].players, t.players):
                    p.tournament = null_tournament
                    p.add_stats(p1.get_stats())
            teams[t.name].tournament = null_tournament
            teams[t.name].add_stats(t.get_stats())
    return list(teams.values())


def get_all_players(comps: dict[str, Tournament]) -> list[Player]:
    players = {}
    for i in comps.values():
        for t in i.teams:
            for p in t.players:

                if p.name in players:
                    players[p.name].add_stats(p.get_stats())
                else:
                    players[p.name] = p
    return list(players.values())


def get_all_officials(comps: dict[str, Tournament]) -> list[Official]:
    officials = []
    names = []
    for i in comps.values():
        officials += [j for j in i.officials if j.name not in names]
        names += [j.name for j in i.officials if j.name not in names]
    return officials
