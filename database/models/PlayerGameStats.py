"""Defines the comments object and provides functions to get and manipulate one"""
import time

from database import db
from database.models import Games


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
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

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
    is_best_player = db.Column(db.Boolean(), default=0, nullable=False)
    faults = db.Column(db.Integer(), default=0, nullable=False)
    double_faults = db.Column(db.Integer(), default=0, nullable=False)
    served_points = db.Column(db.Integer(), default=0, nullable=False)
    served_points_won = db.Column(db.Integer(), default=0, nullable=False)
    serves_received = db.Column(db.Integer(), default=0, nullable=False)
    serves_returned = db.Column(db.Integer(), default=0, nullable=False)
    ace_streak = db.Column(db.Integer(), default=0, nullable=False)
    serve_streak = db.Column(db.Integer(), default=0, nullable=False)
    warnings = db.Column(db.Integer(), default=0, nullable=False)
    green_cards = db.Column(db.Integer(), default=0, nullable=False)
    yellow_cards = db.Column(db.Integer(), default=0, nullable=False)
    red_cards = db.Column(db.Integer(), default=0, nullable=False)
    card_time = db.Column(db.Integer(), default=0, nullable=False)
    card_time_remaining = db.Column(db.Integer(), default=0, nullable=False)
    start_side = db.Column(db.Text())

    tournament = db.relationship("Tournaments", foreign_keys=[tournament_id])
    player = db.relationship("People", foreign_keys=[player_id])
    team = db.relationship("Teams", foreign_keys=[team_id])
    opponent = db.relationship("Teams", foreign_keys=[opponent_id])
    game = db.relationship("Games", foreign_keys=[game_id])

    rows = {
        "Rounds on Court": rounds_on_court,
        "Rounds Carded": rounds_carded,
        "Points Scored": points_scored,
        "Aces Scored": aces_scored,
        "Faults": faults,
        "Double Faults": double_faults,
        "Served Points": served_points,
        "Served Points Won": served_points_won,
        "Serves Received": serves_received,
        "Serves Returned": serves_returned,
        "Warnings": warnings,
        "Green Cards": green_cards,
        "Yellow Cards": yellow_cards,
        "Red Cards": red_cards,
        "Cards": green_cards + yellow_cards + red_cards,
        "Elo": None,
        "Elo Delta": None,
        "Result": Games.winning_team_id == team_id,
        "IGA Side": Games.iga_side_id == team_id,
        "Ranked": Games.ranked,
        "Return Rate": serves_returned / serves_received
    }

    def reset_stats(self):
        self.rounds_on_court = 0
        self.rounds_carded = 0
        self.points_scored = 0
        self.aces_scored = 0
        self.faults = 0
        self.double_faults = 0
        self.served_points = 0
        self.served_points_won = 0
        self.serves_received = 0
        self.serves_returned = 0
        self.warnings = 0
        self.green_cards = 0
        self.yellow_cards = 0
        self.red_cards = 0
        self.card_time = 0
        self.card_time_remaining = 0
        self.is_best_player = 0

    def stats(self, admin=False):
        from database.models import GameEvents
        first_ge = GameEvents.query.filter(GameEvents.game_id == self.game_id).first()
        d = self.game.stats() | {
            "Rounds on Court": self.rounds_on_court,
            "Ranked": self.game.ranked,
            "Rounds Carded": self.rounds_carded,
            "Points Scored": self.points_scored,
            "Aces Scored": self.aces_scored,
            "Faults": self.faults,
            "Double Faults": self.double_faults,
            "Served Points": self.served_points,
            "Served Points Won": self.served_points_won,
            "Serves Received": self.serves_received,
            "Serves Returned": self.serves_returned,
            "Warnings": self.warnings,
            "Green Cards": self.green_cards,
            "Yellow Cards": self.yellow_cards,
            "Red Cards": self.red_cards,
            "Cards": self.red_cards + self.yellow_cards + self.green_cards,
            "Elo": round(self.player.elo(self.game_id), 2),
            "Elo Delta": round(self.player.elo(self.game_id) - self.player.elo(self.game_id - 1), 2),
            "Result": int(self.team_id == self.game.winning_team_id),
            "IGA Side": int(self.team_id == self.game.iga_side_id),
            "Served First": first_ge and int(self.team_id == first_ge.team_to_serve_id),
            "Return Rate": self.serves_returned / (self.serves_received or 1),
            "Timeouts Used": (
                self.game.team_one_timeouts if self.game.team_one_id == self.team_id else self.game.team_two_timeouts),
        }
        if admin:
            d["Penalty Points"] = self.green_cards * 2 + self.yellow_cards * 5 + self.red_cards * 10
        return d

    @classmethod
    def row_by_name(cls, name):
        return cls.rows[name]

    def as_dict(self, include_game=True):
        d = {
                "team": self.team.as_dict(),
                "roundsOnCourt": self.rounds_on_court,
                "roundsCarded": self.rounds_carded,
                "pointsScored": self.points_scored,
                "acesScored": self.aces_scored,
                "isBestPlayer": self.is_best_player,
                "faults": self.faults,
                "doubleFaults": self.double_faults,
                "servedPoints": self.served_points,
                "servedPointsWon": self.served_points_won,
                "servesReceived": self.serves_received,
                "servesReturned": self.serves_returned,
                "aceStreak": self.ace_streak,
                "serveStreak": self.serve_streak,
                "warnings": self.warnings,
                "greenCards": self.green_cards,
                "yellowCards": self.yellow_cards,
                "redCards": self.red_cards,
                "cardTime": self.card_time,
                "cardTimeRemaining": self.card_time_remaining,
                "startSide": self.start_side,
                "elo": round(self.player.elo(self.game_id), 2),
                "eloDelta": round(self.player.elo(self.game_id) - self.player.elo(self.game_id - 1), 2),
            } | self.player.as_dict()
        if include_game:
            d["game"] = self.game.as_dict()
        return d
