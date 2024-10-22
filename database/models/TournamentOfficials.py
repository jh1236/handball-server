"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db


# create table main.tournamentOfficials
# (
#     id           INTEGER
# primary key autoincrement,
# tournamentId INTEGER references main.tournaments,
# officialId   INTEGER references main.officials
# );


class TournamentOfficials(db.Model):
    __tablename__ = "tournamentOfficials"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    tournament_id = db.Column(db.Integer(), db.ForeignKey("tournaments.id"), nullable=False)
    official_id = db.Column(db.Integer(), db.ForeignKey("officials.id"), nullable=False)
    is_scorer = db.Column(db.Boolean(), default=True, nullable=False)
    is_umpire = db.Column(db.Boolean(), default=True, nullable=False)

    tournament = db.relationship("Tournaments")
    official = db.relationship("Officials")

    @property
    def games_umpired(self):
        from database.models import Games
        return Games.query.filter(Games.tournament_id == self.tournament_id, Games.official_id == self.official_id).count()

    @property
    def court_one_umpired(self):
        from database.models import Games
        return Games.query.filter(Games.tournament_id == self.tournament_id, Games.official_id == self.official_id,
                                  Games.court == 0).count()

    @property
    def court_two_umpired(self):
        from database.models import Games
        return Games.query.filter(Games.tournament_id == self.tournament_id, Games.official_id == self.official_id,
                                  Games.court == 1).count()

    @property
    def games_scored(self):
        from database.models import Games
        return Games.query.filter(Games.tournament_id == self.tournament_id, Games.scorer_id == self.official_id).count()
