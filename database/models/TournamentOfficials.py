"""Defines the comments object and provides functions to get and manipulate one"""

from datetime import datetime

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
    created_at = db.Column(db.DateTime(), default=datetime.now, nullable=False)

    # Set fields
    tournament_id = db.Column(db.Integer(), db.ForeignKey("tournaments.id"), nullable=False)
    official_id = db.Column(db.Integer(), db.ForeignKey("officials.id"), nullable=False)
    is_scorer = db.Column(db.Boolean(), default=True, nullable=False)
    is_umpire = db.Column(db.Boolean(), default=True, nullable=False)

    tournament = db.relationship("Tournaments")
    official = db.relationship("Officials")
