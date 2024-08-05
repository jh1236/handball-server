"""Defines the comments object and provides functions to get and manipulate one"""
import time
import typing

from FixtureGenerators.FixturesGenerator import get_type_from_name
from database import db
from database.models import TournamentTeams

if typing.TYPE_CHECKING:
    from database.models import Teams


# create table tournaments
# (
#     id                INTEGER
# primary key autoincrement,
# name              TEXT,
# searchableName    TEXT,
# fixturesGenerator TEXT,
# finalsGenerator   TEXT,
# ranked            INTEGER,
# twoCourts         INTEGER,
# isFinished        INTEGER,
# inFinals          INTEGER,
# isPooled          INTEGER,
# notes             TEXT,
# imageURL          TEXT
# );
def sorter(teams, tournament) -> list[tuple["Teams", dict[str, float]]]:
    from database.models import Games
    pass_one = sorted(teams, key=lambda s: (
    -s[1]["Percentage"], -s[1]["Point Difference"], -s[1]["Points Scored"], s[1]["Red Cards"],
    s[1]["Yellow Cards"], s[1]["Green Cards"], s[1]["Double Faults"], s[1]["Faults"], s[1]["Timeouts Called"]))
    re_sort = False
    for i, next_i in zip(pass_one, pass_one[1:]):
        if i[1]["Percentage"] == next_i[1]["Percentage"]:
            if i[1]["Point Difference"] == next_i[1]["Point Difference"]:
                re_sort = True
                break
    if not re_sort or not tournament:
        return pass_one
    pools = []
    prev_percent = None
    prev_diff = None
    for i in pass_one:
        if i[1]["Percentage"] != prev_percent or i[1]["Point Difference"] != prev_diff:
            prev_percent = i[1]["Percentage"]
            prev_diff = i[1]["Point Difference"]
            pools.append([i])
            continue
        pools[-1].append(i)

    points = {}
    for i in pools:
        if len(i) == 1:
            points[i[0][0].team_id] = 0
            continue
        for j, t1 in enumerate(i):
            points[t1[0].team_id] = 0
            for t2 in i[j:]:
                games = Games.query.filter((Games.team_one_id == t1[0].team_id) | (Games.team_two_id == t1[0].team_id),
                                           (Games.team_one_id == t2[0].team_id) | (Games.team_two_id == t2[0].team_id),
                                           Games.ended == True, Games.tournament_id == tournament.id).all()
                for g in games:
                    points[g.winning_team_id] += 1
    return sorted(teams, key=lambda s: (
        -s[1]["Percentage"], -s[1]["Point Difference"], points[s[0].team_id], -s[1]["Points Scored"], s[1]["Red Cards"],
        s[1]["Yellow Cards"], s[1]["Green Cards"], s[1]["Double Faults"], s[1]["Faults"], s[1]["Timeouts Called"]))


def beautify_stats(stats):
    from database.models.Teams import PERCENTAGES
    for i in stats:
        for k, v in i[1].items():
            if k in PERCENTAGES:
                i[1][k] = f"{100.0 * v: .2f}%"
            elif isinstance(v, float):
                i[1][k] = round(v, 2)
    return stats


class Tournaments(db.Model):
    __tablename__ = "tournaments"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    name = db.Column(db.Text(), nullable=False)
    searchable_name = db.Column(db.Text(), nullable=False)
    fixtures_type = db.Column(db.Text(), nullable=False)
    finals_type = db.Column(db.Text())
    ranked = db.Column(db.Boolean(), nullable=False)
    two_courts = db.Column(db.Boolean(), nullable=False)
    has_scorer = db.Column(db.Boolean(), nullable=False)
    finished = db.Column(db.Boolean(), nullable=False)
    in_finals = db.Column(db.Boolean(), nullable=False)
    is_pooled = db.Column(db.Boolean(), nullable=False)
    notes = db.Column(db.Text(), nullable=False)
    image_url = db.Column(db.Text(), nullable=False)
    badminton_serves = db.Column(db.Boolean(), nullable=False)

    def ladder(self):
        teams = [(i, i.stats(make_nice=False)) for i in
                 TournamentTeams.query.filter(TournamentTeams.tournament_id == self.id,
                                              TournamentTeams.team_id != 1).all()]

        teams = beautify_stats(sorter(teams, self))
        if get_type_from_name(self.fixtures_type, self).manual_allowed():
            teams = [i for i in teams if i[1]["Games Played"]]
        if self.is_pooled:
            return [[(i[0].team, i[1]) for i in teams if i[0].pool == 1],
                    [(i[0].team, i[1]) for i in teams if i[0].pool == 2]]
        teams = [(i[0].team, i[1]) for i in teams]
        return teams

    @classmethod
    def all_time_ladder(cls):
        from database.models import Teams
        teams = [(i, i.stats(make_nice=False)) for i in
                 Teams.query.filter(Teams.id != 1).all()]
        teams = beautify_stats(sorter(teams, None))
        teams = [i for i in teams if i[1]["Games Played"]]
        return teams
