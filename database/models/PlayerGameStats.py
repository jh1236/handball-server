"""Defines the comments object and provides functions to get and manipulate one"""

from datetime import datetime

from database import db


# create table main.playerGameStats
# (
#     id                INTEGER primary key autoincrement,
# gameId            INTEGER references main.games,
# playerId          INTEGER references main.people,
# teamId            INTEGER references main.teams,
# opponentId        INTEGER references main.teams,
# tournamentId      INTEGER references main.tournaments,
# roundsPlayed      INTEGER,
# roundsBenched     INTEGER,
# isBestPlayer      INTEGER,
# isFinal           INTEGER,
# points            INTEGER,
# aces              INTEGER,
# faults            INTEGER,
# servedPoints      INTEGER,
# servedPointsWon   INTEGER,
# servesReceived    INTEGER,
# servesReturned    INTEGER,
# doubleFaults      INTEGER,
# greenCards        INTEGER,
# warnings          INTEGER,
# yellowCards       INTEGER,
# redCards          INTEGER,
# cardTimeRemaining INTEGER,
# cardTime          INTEGER,
# startSide         TEXT
# );


class PlayerGameStats(db.Model):
    __tablename__ = "playerGameStats"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), default=datetime.now, nullable=False)

    # Set fields
    game_id = db.Column(db.Integer(), db.ForeignKey("games.id"), nullable=False)
    player_id = db.Column(db.Integer(), db.ForeignKey("people.id"), nullable=False)
    team_id = db.Column(db.Integer(), db.ForeignKey("teams.id"), nullable=False)
    opponent_id = db.Column(db.Integer(), db.ForeignKey("teams.id"), nullable=False)
    tournament_id = db.Column(db.Integer(), db.ForeignKey("tournaments.id"), nullable=False)
    rounds_on_court = db.Column(db.Integer(), default=0, nullable=False)
    rounds_carded = db.Column(db.Integer(), default=0, nullable=False)
    points_scored = db.Column(db.Integer(), default=0, nullable=False)
    aces_scored = db.Column(db.Integer(), default=0, nullable=False)
    faults = db.Column(db.Integer(), default=0, nullable=False)
    double_faults = db.Column(db.Integer(), default=0, nullable=False)
    points_served = db.Column(db.Integer(), default=0, nullable=False)
    points_served_won = db.Column(db.Integer(), default=0, nullable=False)
    serves_received = db.Column(db.Integer(), default=0, nullable=False)
    serves_returned = db.Column(db.Integer(), default=0, nullable=False)
    warnings = db.Column(db.Integer(), default=0, nullable=False)
    green_cards = db.Column(db.Integer(), default=0, nullable=False)
    yellow_cards = db.Column(db.Integer(), default=0, nullable=False)
    red_cards = db.Column(db.Integer(), default=0, nullable=False)
    card_time = db.Column(db.Integer(), default=0, nullable=False)
    card_time_remaining = db.Column(db.Integer(), default=0, nullable=False)
    start_side = db.Column(db.Text())

    tournament = db.relationship("Tournaments", foreign_keys=[tournament_id])
    team = db.relationship("Teams", foreign_keys=[team_id])
    opponent = db.relationship("Teams", foreign_keys=[opponent_id])
    game = db.relationship("Games", foreign_keys=[game_id])

