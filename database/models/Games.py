"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db


# create table main.games
# (
#     id                INTEGER primary key autoincrement,
# tournamentId      INTEGER references main.tournaments,
# teamOne           INTEGER references main.teams,
# teamTwo           INTEGER references main.teams,
# teamOneScore      INTEGER,
# teamTwoScore      INTEGER,
# teamOneTimeouts   INTEGER,
# teamTwoTimeouts   INTEGER,
# winningTeam       INTEGER,
# started           INTEGER,
# ended             INTEGER,
# someoneHasWon     INTEGER,
# protested         INTEGER,
# resolved          INTEGER,
# isRanked          INTEGER,
# bestPlayer        INTEGER references main.people,
# official          INTEGER references main.officials,
# scorer            INTEGER references main.officials,
# IGASide           INTEGER references main.teams,
# gameStringVersion INTEGER,
# gameString        TEXT,
# playerToServe     INTEGER references main.people,
# teamToServe       INTEGER references main.teams,
# sideToServe       TEXT,
# startTime         INTEGER,
# length            INTEGER,
# court             INTEGER,
# isFinal           INTEGER,
# round             INTEGER,
# notes             TEXT,
# isBye             INTEGER,
# pool              INTEGER,
# status            TEXT,
# adminStatus       TEXT,
# noteableStatus    TEXT
# );


class Games(db.Model):
    __tablename__ = "games"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    tournament_id = db.Column(db.Integer(), db.ForeignKey("tournaments.id"), nullable=False)
    team_one_id = db.Column(db.Integer(), db.ForeignKey("teams.id"), nullable=False)
    team_two_id = db.Column(db.Integer(), db.ForeignKey("teams.id"), nullable=False)
    team_one_score = db.Column(db.Integer(), default=0, nullable=False)
    team_two_score = db.Column(db.Integer(), default=0, nullable=False)
    team_one_timeouts = db.Column(db.Integer(), default=0, nullable=False)
    team_two_timeouts = db.Column(db.Integer(), default=0, nullable=False)
    winning_team_id = db.Column(db.Integer(), db.ForeignKey("teams.id"))
    started = db.Column(db.Boolean(), default=False, nullable=False)
    someone_has_won = db.Column(db.Boolean(), default=False, nullable=False)
    ended = db.Column(db.Boolean(), default=False, nullable=False)
    protested = db.Column(db.Boolean(), default=False, nullable=False)
    resolved = db.Column(db.Boolean(), default=False, nullable=False)
    ranked = db.Column(db.Boolean(), nullable=False)
    best_player_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    official_id = db.Column(db.Integer(), db.ForeignKey("officials.id"), nullable=False)
    scorer_id = db.Column(db.Integer(), db.ForeignKey("officials.id"))
    iga_side_id = db.Column(db.Integer(), db.ForeignKey("teams.id"))
    player_to_serve_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    team_to_serve_id = db.Column(db.Integer(), db.ForeignKey("teams.id"))
    side_to_serve = db.Column(db.Text(), default='Left', nullable=False)
    start_time = db.Column(db.Integer())
    length = db.Column(db.Integer())
    court = db.Column(db.Integer(), default=0, nullable=False)
    is_final = db.Column(db.Boolean(), default=False, nullable=False)
    round = db.Column(db.Integer(), nullable=False)
    notes = db.Column(db.Text())
    is_bye = db.Column(db.Boolean(), default=False, nullable=False)
    status = db.Column(db.Text(), default='Waiting For Start', nullable=False)
    admin_status = db.Column(db.Text(), default='Waiting For Start', nullable=False)
    noteable_status = db.Column(db.Text(), default='Waiting For Start', nullable=False)

    tournament = db.relationship("Tournaments", foreign_keys=[tournament_id])
    team_one = db.relationship("Teams", foreign_keys=[team_one_id])
    team_two = db.relationship("Teams", foreign_keys=[team_two_id])
    best_player = db.relationship("People", foreign_keys=[best_player_id])
    official = db.relationship("Officials", foreign_keys=[official_id])
    scorer = db.relationship("Officials", foreign_keys=[scorer_id])
    iga_side = db.relationship("Teams", foreign_keys=[iga_side_id])
    player_to_serve = db.relationship("People", foreign_keys=[player_to_serve_id])
    team_to_serve = db.relationship("Teams", foreign_keys=[team_to_serve_id])

    def reset(self):
        self.started = False
        self.someone_has_won = False
        self.ended = False
        self.protested = False
        self.resolved = False
        self.best_player_id = None
        self.team_one_score = 0
        self.team_two_score = 0
        self.team_one_timeouts = 0
        self.team_two_timeouts = 0
        self.notes = None
        self.winning_team_id = None
