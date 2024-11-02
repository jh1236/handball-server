"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db


# create table main.officials
# (
#     id          INTEGER
# primary key autoincrement,
# personId    INTEGER
# references main.people,
# isAdmin     INTEGER,
# proficiency INTEGER
# );


class Officials(db.Model):
    __tablename__ = "officials"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    person_id = db.Column(db.Integer(), db.ForeignKey("people.id"), nullable=False)
    proficiency = db.Column(db.Text(), nullable=False)

    person = db.relationship("People", foreign_keys=[person_id])

    def stats(self, tournament=None):
        from database.models import PlayerGameStats
        from database.models import Games
        stats = {
            "Green Cards Given": 0,
            "Yellow Cards Given": 0,
            "Red Cards Given": 0,
            "Cards Given": 0,
            "Cards Per Game": 0,
            "Faults Called": 0,
            "Faults Per Game": 0,
            "Games Umpired": 0,
            "Games Scored": 0,
            "Rounds Umpired": 0
        }
        q = db.session.query(PlayerGameStats).join(Games, Games.id == PlayerGameStats.game_id).filter(
            Games.official_id == self.id)
        if tournament:
            q = q.filter(Games.tournament_id == tournament.id)
        prev_game_id = -1
        for pgs in q.all():
            stats["Green Cards Given"] += pgs.green_cards
            stats["Yellow Cards Given"] += pgs.yellow_cards
            stats["Red Cards Given"] += pgs.red_cards
            stats["Cards Given"] += pgs.green_cards + pgs.yellow_cards + pgs.red_cards
            stats["Faults Called"] += pgs.faults
            if pgs.game_id > prev_game_id:
                stats["Games Umpired"] += 1
                stats["Rounds Umpired"] += pgs.game.team_one_score + pgs.game.team_two_score
        q = Games.query.filter(Games.scorer_id == self.id)

        if tournament:
            q = q.filter(Games.tournament_id == tournament.id)
        stats["Games Scored"] = len(q.all())
        stats["Cards Per Game"] = round(stats["Cards Given"] / (stats["Games Umpired"] or 1), 2)
        stats["Faults Per Game"] = round(stats["Faults Called"] / (stats["Games Umpired"] or 1), 2)
        return stats

    def as_dict(self, tournament=None):
        return self.person.as_dict(include_stats=False) | {"stats": self.stats(tournament=tournament)}
