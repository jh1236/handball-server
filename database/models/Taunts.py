"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db


# create table main.taunts
# (
#     id    INTEGER primary key autoincrement,
# event TEXT,
# taunt TEXT
# );
#


class Taunts(db.Model):
    __tablename__ = "taunts"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    event = db.Column(db.Text(), nullable=False)
    taunt = db.Column(db.Text(), nullable=False)
