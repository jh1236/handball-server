"""Defines the comments object and provides functions to get and manipulate one"""

from datetime import datetime

from database import db


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


class Tournaments(db.Model):
    __tablename__ = "tournaments"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), default=datetime.now, nullable=False)

    # Set fields
    name = db.Column(db.Text(), nullable=False)
    searchable_name = db.Column(db.Text(), nullable=False)
    fixtures_type = db.Column(db.Text(), nullable=False)
    finals_type = db.Column(db.Text())
    ranked = db.Column(db.Boolean(), nullable=False)
    two_courts = db.Column(db.Boolean(), nullable=False)
    finished = db.Column(db.Boolean(), nullable=False)
    finals = db.Column(db.Boolean(), nullable=False)
    pooled = db.Column(db.Boolean(), nullable=False)
    notes = db.Column(db.Text(), nullable=False)
    imageUrl = db.Column(db.Text(), nullable=False)
