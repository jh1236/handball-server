"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db


# create table main.tournamentTeams
# (
#     id             INTEGER
# primary key autoincrement,
# tournamentId   INTEGER references main.tournaments,
# teamId         INTEGER references main.teams,
# pool           INTEGER
# );


class TournamentTeams(db.Model):
    __tablename__ = "tournamentTeams"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    tournament_id = db.Column(db.Integer(), db.ForeignKey("tournaments.id"), nullable=False)
    team_id = db.Column(db.Integer(), db.ForeignKey("teams.id"), nullable=False)
    pool = db.Column(db.Integer())

    tournament = db.relationship("Tournaments")
    team = db.relationship("Teams")
