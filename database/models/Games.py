"""Defines the comments object and provides functions to get and manipulate one"""
import time
import typing

from database import db

if typing.TYPE_CHECKING:
    pass


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
    serve_timer = db.Column(db.Integer())
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
    elo_delta = db.relationship("EloChange")

    row_titles = ["Rounds",
                  "Score Difference",
                  "Elo Gap",
                  "Length",
                  "Cards",
                  "Warnings",
                  "Green Cards",
                  "Yellow Cards",
                  "Red Cards",
                  "Timeouts Used",
                  "Aces Scored",
                  "Ace Percentage",
                  "Faults",
                  "Fault Percentage",
                  "Start Time",
                  "Court",
                  "Timeline",
                  "Umpire",
                  "Format",
                  "Tournament"
                  ]

    @property
    def teams_protested(self):
        from database.models import GameEvents
        events = GameEvents.query.filter(GameEvents.game_id == self.id, GameEvents.event_type == 'Protest').all()
        return events

    @property
    def formatted_start_time(self):
        if self.start_time < 0: return "??"
        return time.strftime("%d/%m/%y (%H:%M)", time.localtime(self.start_time))

    @property
    def formatted_length(self):
        if self.start_time < 0: return "??"
        return time.strftime("(%H:%M:%S)", time.localtime(self.length))

    @property
    def losing_team_id(self):
        # cheeky maths hack
        return self.team_two_id + self.team_two_id - self.winning_team_id

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

    def stats(self):
        from database.models import PlayerGameStats
        pgs = PlayerGameStats.query.filter(PlayerGameStats.game_id == self.id).all()
        return {
            "Rounds": self.team_one_score + self.team_two_score,
            "Score Difference": abs(self.team_one_score - self.team_two_score),
            "Elo Gap": abs(self.team_one.elo(self.id) - self.team_two.elo(self.id)),
            "Length": self.length,
            "Cards": sum(i.green_cards + i.yellow_cards + i.red_cards for i in pgs),
            "Warnings": sum(i.warnings for i in pgs),
            "Green Cards": sum(i.green_cards for i in pgs),
            "Yellow Cards": sum(i.yellow_cards for i in pgs),
            "Red Cards": sum(i.red_cards for i in pgs),
            "Aces Scored": sum(i.aces_scored for i in pgs),
            "Ace Percentage": sum(i.aces_scored for i in pgs) / ((self.team_one_score + self.team_two_score) or 1),
            "Faults": sum(i.faults for i in pgs),
            "Fault Percentage": sum(i.faults for i in pgs) / ((self.team_one_score + self.team_two_score) or 1),
            "Start Time": 0 if not self.start_time or self.start_time <= 0 else (self.start_time - Games.query.filter(
                Games.start_time > 0).order_by(Games.start_time).first().start_time) / (24.0 * 60 * 60 * 60),
            "Court": self.court,
            "Ranked": self.ranked,
            "Timeline": self.id,
            "Umpire": self.official.person.name if self.official else "None",
            "Format": "Practice" if self.tournament_id == 1 else "Championship",
            "Tournament": self.tournament.name,
        }

    def as_dict(self, admin_view=False, include_game_events=False):
        d = {
            "id": self.id,
            "tournament": self.tournament.as_dict(),
            "team_one": self.team_one.as_dict(),
            "team_two": self.team_two.as_dict(),
            "team_one_score": self.team_one_score,
            "team_two_score": self.team_two_score,
            "team_one_timeouts": self.team_one_timeouts,
            "team_two_timeouts": self.team_two_timeouts,
            "first_team_winning": self.winning_team_id == self.team_one_id,
            "started": self.started,
            "someone_has_won": self.someone_has_won,
            "ended": self.ended,
            "protested": self.protested,
            "resolved": self.resolved,
            "ranked": self.ranked,
            "best_player": self.best_player.as_dict() if self.best_player else None,
            "official": self.official.as_dict(tournament=self.tournament) if self.official else None,
            "scorer": self.scorer.as_dict(tournament=self.tournament) if self.scorer else None,
            "first_team_iga": self.iga_side_id == self.team_one_id,
            "first_team_to_serve": self.team_to_serve_id == self.team_one_id,
            "side_to_serve": self.side_to_serve,
            "start_time": self.start_time,
            "serve_timer": self.serve_timer,
            "length": self.length,
            "court": self.court,
            "is_final": self.is_final,
            "round": self.round,
            "is_bye": self.is_bye,
            "status": self.status,
        }
        if admin_view:
            d |= {
                "admin_status": self.admin_status,
                "noteable_status": self.noteable_status,
                "notes": self.notes,
            }
        if include_game_events:
            from database.models import GameEvents
            d["Events"] = [i.as_dict(include_game=False) for i in GameEvents.query.filter(GameEvents.game_id == self.id).all()]

        return d
