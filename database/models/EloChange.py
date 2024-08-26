"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db


# create table main.eloChange
# (
#     id           INTEGER
# primary key autoincrement,
# gameId       INTEGER references main.games,
# playerId     INTEGER references main.people,
# tournamentId INTEGER references main.tournaments,
# eloChange    INTEGER
# );


class EloChange(db.Model):
    __tablename__ = "eloChange"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    game_id = db.Column(db.Integer(), db.ForeignKey("games.id"), nullable=False)
    tournament_id = db.Column(db.Integer(), db.ForeignKey("tournaments.id"), nullable=False)
    player_id = db.Column(db.Integer(), db.ForeignKey("people.id"), nullable=False)
    elo_delta = db.Column(db.Integer(), nullable=False)

    player = db.relationship("People", foreign_keys=[player_id])
    tournament = db.relationship("Tournaments", foreign_keys=[tournament_id])
