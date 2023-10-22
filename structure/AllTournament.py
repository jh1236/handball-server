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
                if p.name not in players:
                    players[p.name] = Player(p.name)
                    players[p.name]._team = t
                if not p.team.has_photo and t.has_photo:
                    players[p.name]._team = t
                players[p.name].add_stats(p.get_stats())
    return list(players.values())


def get_all_officials(comps: dict[str, Tournament]) -> list[Official]:
    officials = {}
    for i in comps.values():
        for j in i.officials:
            if j.nice_name() not in officials:
                officials[j.nice_name()] = Official(j.name, "", [])
            officials[j.nice_name()].add_stats(j.get_stats())
    return list(officials.values())
