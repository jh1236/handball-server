"""Defines the comments object and provides functions to get and manipulate one"""

from datetime import datetime

from database import db


# create table main.teams
# (
#     id             INTEGER
# primary key autoincrement,
# name           TEXT,
# searchableName TEXT,
# imageURL       TEXT,
# primaryColor   TEXT,
# secondaryColor TEXT,
# captain        INTEGER
# references main.people,
# nonCaptain     INTEGER
# references main.people,
# substitute     INTEGER
# references main.people
# );


class Teams(db.Model):
    __tablename__ = "teams"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), default=datetime.now, nullable=False)

    # Set fields
    name = db.Column(db.Text(), nullable=False)
    searchable_name = db.Column(db.Text(), nullable=False)
    image_url = db.Column(db.Text())
    primary_color = db.Column(db.Text())
    secondary_color = db.Column(db.Text())
    captain_id = db.Column(db.Integer(), db.ForeignKey("people.id"), nullable=False)
    non_captain_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    substitute_id = db.Column(db.Integer(), db.ForeignKey("people.id"))

    captain = db.relationship("People", foreign_keys=[captain_id])
    non_captain = db.relationship("People", foreign_keys=[non_captain_id])
    substitute = db.relationship("People", foreign_keys=[substitute_id])
