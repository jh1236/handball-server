"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db


# create table main.people
# (
#     id             INTEGER
# primary key autoincrement,
# name           TEXT,
# searchableName TEXT,
# password       TEXT,
# imageURL       TEXT,
# sessionToken   TEXT,
# tokenTimeout   INTEGER
# );
#

class People(db.Model):
    __tablename__ = "people"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    name = db.Column(db.Text(), nullable=False)
    searchable_name = db.Column(db.Text(), nullable=False)
    password = db.Column(db.Text())
    image_url = db.Column(db.Text())
    session_token = db.Column(db.Text())
    token_timeout = db.Column(db.Integer())
