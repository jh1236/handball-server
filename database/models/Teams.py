import time

from database import db

# create table main.teams
# (
#     id             INTEGER
# primary key autoincrement,
# name           TEXT,
# searchableName TEXT,
# imageURL       TEXT,
# primaryColor   TEXT,
# secondaryColor TEXT,
# captain        INTEGER
# references main.people,
# nonCaptain     INTEGER
# references main.people,
# substitute     INTEGER
# references main.people
# );

PERCENTAGES = [
    "Percentage"
]


class Teams(db.Model):
    __tablename__ = "teams"

    # Auto-initialised fields
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.Integer(), default=time.time, nullable=False)

    # Set fields
    name = db.Column(db.Text(), nullable=False)
    searchable_name = db.Column(db.Text(), nullable=False)
    image_url = db.Column(db.Text())
    primary_color = db.Column(db.Text())
    secondary_color = db.Column(db.Text())
    captain_id = db.Column(db.Integer(), db.ForeignKey("people.id"), nullable=False)
    non_captain_id = db.Column(db.Integer(), db.ForeignKey("people.id"))
    substitute_id = db.Column(db.Integer(), db.ForeignKey("people.id"))

    captain = db.relationship("People", foreign_keys=[captain_id])
    non_captain = db.relationship("People", foreign_keys=[non_captain_id])
    substitute = db.relationship("People", foreign_keys=[substitute_id])

    def elo(self, last_game=None):
        from database.models import People
        players = People.query.filter(
            (People.id == self.captain_id) | (People.id == self.non_captain_id) | (
                    People.id == self.substitute_id)).all()
        if not players:
            return 1500.0
        elos = []
        for i in players:
            elos.append(i.elo(last_game))
        return sum(elos) / len(elos)

    @property
    def short_name(self):
        return self.name if len(self.name) < 30 else self.name[:27] + "..."

    def players(self):
        return [i for i in [self.captain, self.non_captain, self.substitute] if i]

    def stats(self, games_filter=None, make_nice=True, ranked=True):

        from database.models import PlayerGameStats, Games
        games = Games.query.filter((Games.team_one_id == self.id) | (Games.team_two_id == self.id),
                                   Games.is_bye == False, Games.is_final == False)
        pgs = PlayerGameStats.query.join(Games, PlayerGameStats.game_id == Games.id).filter(
            Games.is_bye == False, Games.is_final == False,
            PlayerGameStats.team_id == self.id)
        # '== False' is not an error here, as Model overrides __eq__, so using a not operator provides a different result
        if self.non_captain_id is not None and ranked:
            games = games.filter(Games.ranked)
            pgs = pgs.filter(Games.ranked)

        if games_filter:
            games = games_filter(games)
            pgs = games_filter(pgs)

        games = games.all()
        pgs = pgs.all()

        ret = {
            "Elo": self.elo(games[-1].id if games else 9999999),
            "Games Played": len([i for i in games if i.started]),
            "Games Won": sum(i.winning_team_id == self.id for i in games if i.ended),
            "Games Lost": sum(i.winning_team_id != self.id for i in games if i.ended),
            "Percentage": sum(i.winning_team_id == self.id for i in games if i.ended) / (
                    len([i for i in games if i.ended]) or 1),
            "Green Cards": sum(i.green_cards for i in pgs),
            "Yellow Cards": sum(i.yellow_cards for i in pgs),
            "Red Cards": sum(i.red_cards for i in pgs),
            "Faults": sum(i.faults for i in pgs),
            "Double Faults": sum(i.double_faults for i in pgs),
            "Timeouts Called": sum(
                (i.team_one_timeouts if i.team_one_id == self.id else i.team_two_timeouts) for i in games),
            # Points for and against are different because points for shouldn't include opponents double faults, but points against should
            "Points Scored": sum(i.points_scored for i in pgs),
            "Points Against": sum((i.team_two_score if i.team_one_id == self.id else i.team_one_score) for i in games),
            "Point Difference": sum(i.points_scored for i in pgs) - sum(
                (i.team_two_score if i.team_one_id == self.id else i.team_one_score) for i in games),
        }
        if make_nice:
            for k, v in ret.items():
                if k in PERCENTAGES:
                    ret[k] = f"{100.0 * v: .2f}%".strip()
                elif isinstance(v, float):
                    ret[k] = round(v, 2)
        return ret

    @classmethod
    @property
    def BYE(cls):
        return cls.query.filter(cls.id == 1).first()

    def as_dict(self, include_stats=False, tournament=None, include_player_stats=None, make_nice=False):
        include_player_stats = include_stats if include_player_stats is None else include_player_stats
        d = {
            "name": self.name,
            "searchableName": self.searchable_name,
            "imageUrl": self.image_url if not self.image_url.startswith("/") else "https://squarers.org" + self.image_url,
            "primaryColor": self.primary_color,
            "secondaryColor": self.secondary_color,
            "captain": self.captain.as_dict(include_stats=include_player_stats,
                                            tournament=tournament) if self.captain else None,
            "nonCaptain": self.non_captain.as_dict(include_stats=include_player_stats,
                                                    tournament=tournament) if self.non_captain else None,
            "substitute": self.substitute.as_dict(include_stats=include_player_stats,
                                                  tournament=tournament) if self.substitute else None,
        }
        if include_stats:
            from database.models import Games
            game_filter = (lambda a: a.filter(Games.tournament_id == tournament)) if tournament else None
            d["stats"] = self.stats(game_filter, make_nice=make_nice)
        return d
