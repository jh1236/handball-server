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