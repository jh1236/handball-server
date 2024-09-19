"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db
from database.models import People


# create table main.gameEvents
# (
#     id                INTEGER primary key autoincrement,
# gameId            INTEGER references main.games,
# teamId            INTEGER references main.teams,
# playerId          INTEGER references main.people,
# tournamentId      INTEGER references main.tournaments,
# eventType         TEXT,
# details           INTEGER,
# notes             TEXT,
# playerWhoServed   INTEGER references main.people,
# teamWhoServed     INTEGER references main.teams,
# sideServed        TEXT,
# nextPlayerToServe INTEGER references main.people,
# nextTeamToServe   INTEGER references main.teams,
# nextServeSide     TEXT,
# teamOneLeft       INTEGER references main.people,
# teamOneRight      INTEGER references main.people,
# teamTwoLeft       INTEGER references main.people,
# teamTwoRight      INTEGER references main.people
# );


class GameEvents(db.Model):
    __tablename__ = "gameEvents"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    game_id = db.Column(db.Integer(), db.ForeignKey("games.id"), nullable=False)
    tournament_id = db.Column(db.Integer(), db.ForeignKey("tournaments.id"), nullable=False)
    event_type = db.Column(db.Text(), nullable=False)
    team_id = db.Column(db.Integer(), db.ForeignKey("teams.id"))
    player_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    details = db.Column(db.Integer())
    notes = db.Column(db.Text())
    player_who_served_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    team_who_served_id = db.Column(db.Integer(), db.ForeignKey("teams.id"))
    side_served = db.Column(db.Text())
    player_to_serve_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    team_to_serve_id = db.Column(db.Integer(), db.ForeignKey("teams.id"))
    side_to_serve = db.Column(db.Text())
    team_one_left_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    team_one_right_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    team_two_left_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    team_two_right_id = db.Column(db.Integer(), db.ForeignKey("people.id"))

    game = db.relationship("Games", foreign_keys=[game_id])
    team = db.relationship("Teams", foreign_keys=[team_id])
    player = db.relationship("People", foreign_keys=[player_id])
    tournament = db.relationship("Tournaments", foreign_keys=[tournament_id])
    player_who_served = db.relationship("People", foreign_keys=[player_who_served_id])
    team_who_served = db.relationship("Teams", foreign_keys=[team_who_served_id])
    player_to_serve = db.relationship("People", foreign_keys=[player_to_serve_id])
    team_to_serve = db.relationship("Teams", foreign_keys=[team_to_serve_id])
    team_one_left = db.relationship("People", foreign_keys=[team_one_left_id])
    team_one_right = db.relationship("People", foreign_keys=[team_one_right_id])
    team_two_left = db.relationship("People", foreign_keys=[team_two_left_id])
    team_two_right = db.relationship("People", foreign_keys=[team_two_right_id])

    @property
    def other_team(self):
        return self.game.team_two if self.team_id == self.game.team_one_id else self.game.team_one

    @property
    def opposite_player(self):
        print(f"{self.team_id} == {self.game.team_one_id} ({self.team_id == self.game.team_one_id})")
        if self.team_id == self.game.team_one_id:
            return self.team_two_left if self.player_id == self.team_one_left else self.team_two_right
        else:
            return self.team_one_left if self.player_id == self.team_two_left else self.team_one_right

    @property
    def team_mate(self):
        if self.team_id == self.game.team_one_id:
            return self.team_one_left if self.player_id != self.team_one_left else self.team_one_right
        else:
            return self.team_two_left if self.player_id != self.team_two_left else self.team_two_right
