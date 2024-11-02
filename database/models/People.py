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

PERCENTAGES = [
    "Percentage",
    "Serve Ace Rate",
    "Serve Fault Rate",
    "Percentage of Points Scored",
    "Percentage of Points Scored For Team",
    "Percentage of Games Starting Left",
    "Percentage of Points Served Won",
    "Serve Return Rate"
]


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
    is_admin = db.Column(db.Boolean(), nullable=False, default=False)

    def image(self, tournament=None):
        from database.models import Teams
        from database.models import TournamentTeams
        if self.image_url:
            return self.image_url
        if tournament:
            t = Teams.query.join(TournamentTeams, TournamentTeams.team_id == Teams.id).filter(
                (Teams.captain_id == self.id) | (Teams.non_captain_id == self.id) | (
                        Teams.substitute_id == self.id), TournamentTeams.tournament_id == tournament.id).order_by(
                Teams.image_url.like('/api/teams/image?%').desc(),
                Teams.id).first()
        else:
            t = Teams.query.filter((Teams.captain_id == self.id) | (Teams.non_captain_id == self.id) | (
                    Teams.substitute_id == self.id)).order_by(Teams.image_url.like('/api/teams/image?%').desc(),
                                                              Teams.id).first()
        return t.image_url if t else "/api/teams/image?name=bye"

    def elo(self, last_game=None):
        from database.models import EloChange
        elo_deltas = EloChange.query.filter(self.id == EloChange.player_id)
        if last_game:
            elo_deltas = elo_deltas.filter(EloChange.game_id <= last_game)
        return 1500.0 + sum(i.elo_delta for i in elo_deltas)

    def simple_stats(self, games_filter=None, make_nice=True, include_unranked=False, include_solo=False) -> dict[
        str, str | float]:
        from database.models import PlayerGameStats, Games
        from database.models import Teams
        q = db.session.query(Games, PlayerGameStats, Teams).filter(
            PlayerGameStats.game_id == Games.id,
            PlayerGameStats.player_id == self.id,
            Teams.id == PlayerGameStats.team_id)
        q = q.filter(Games.is_bye == False, Games.is_final == False)
        # '== False' is not an error here, as Model overrides __eq__, so using a not operator provides a different result
        if games_filter:
            q = games_filter(q)
        if not include_unranked:
            if not include_solo:
                q = q.filter(Games.ranked)
            else:
                q = q.filter(Games.ranked | (Teams.non_captain_id == None))

        q = q.all()
        games = [i[0] for i in q]
        players = [i[1] for i in q]
        games_played = len(
            [i for i in games if i.started]) or 1  # used as a divisor to save me thinking about div by zero
        ret = {
            "B&F Votes": len([i for i in games if i.best_player_id == self.id]),
            "Elo": self.elo(max([i.id for i in games] + [0])),
            "Games Won": len([g for g, p in zip(games, players) if g.winning_team_id == p.team_id and g.ended]),
            "Games Lost": len([g for g, p in zip(games, players) if g.winning_team_id != p.team_id and g.ended]),
            "Games Played": len([i for i in games if i.started]),
            "Percentage": len([g for g, p in zip(games, players) if g.winning_team_id == p.team_id]) / games_played,
            "Points Scored": sum(i.points_scored for i in players),
            "Points Served": sum(i.served_points for i in players),
            "Aces Scored": sum(i.aces_scored for i in players),
            "Faults": sum(i.faults for i in players),
            "Double Faults": sum(i.double_faults for i in players),
            "Green Cards": sum(i.green_cards for i in players),
            "Yellow Cards": sum(i.yellow_cards for i in players),
            "Red Cards": sum(i.red_cards for i in players)
        }
        for k, v in ret.items():
            if k in PERCENTAGES:
                ret[k] = f"{100.0 * v: .2f}%"
            elif isinstance(v, float):
                ret[k] = round(v, 2)
        return ret

    def stats(self, games_filter=None, make_nice=True, include_unranked=False, include_solo=False, admin=False) -> dict[
        str, str | float]:
        from database.models import PlayerGameStats, Games
        from database.models import EloChange
        from database.models import Teams
        q = db.session.query(Games, PlayerGameStats, EloChange, Teams).outerjoin(
            EloChange, (EloChange.game_id == Games.id) & (EloChange.player_id == self.id)
        ).filter(
            PlayerGameStats.game_id == Games.id,
            PlayerGameStats.player_id == self.id,
            Teams.id == PlayerGameStats.team_id)
        q = q.filter(Games.is_bye == False, Games.is_final == False)
        # '== False' is not an error here, as Model overrides __eq__, so using a not operator provides a different result
        if games_filter:
            q = games_filter(q)
        if not include_unranked:
            if not include_solo:
                q = q.filter(Games.ranked)
            else:
                q = q.filter(Games.ranked | (Teams.non_captain_id == None))

        q = q.all()
        games = [i[0] for i in q]
        players = [i[1] for i in q]
        elo_delta = [i[2] for i in q]
        games_played = len(games) or 1  # used as a divisor to save me thinking about div by zero
        ret = {
            "B&F Votes": len([i for i in games if i.best_player_id == self.id]),
            "Elo": self.elo(max([i.id for i in games] + [0])),
            "Games Won": len([g for g, p in zip(games, players) if g.winning_team_id == p.team_id]),
            "Games Lost": len([g for g, p in zip(games, players) if g.winning_team_id != p.team_id]),
            "Games Played": len([i for i in games if i.started]),
            "Percentage": len([g for g, p in zip(games, players) if g.winning_team_id == p.team_id]) / games_played,
            "Points Scored": sum(i.points_scored for i in players),
            "Points Served": sum(i.served_points for i in players),
            "Aces Scored": sum(i.aces_scored for i in players),
            "Faults": sum(i.faults for i in players),
            "Double Faults": sum(i.double_faults for i in players),
            "Green Cards": sum(i.green_cards for i in players),
            "Yellow Cards": sum(i.yellow_cards for i in players),
            "Red Cards": sum(i.red_cards for i in players),
            "Rounds on Court": sum(i.rounds_on_court for i in players if i),
            "Rounds Carded": sum(i.rounds_carded for i in players),
            "Net Elo Delta": sum(i.elo_delta for i in elo_delta if i),
            "Average Elo Delta": sum(i.elo_delta for i in elo_delta if i) / games_played,
            "Points per Game": sum(i.points_scored for i in players) / games_played,
            "Points per Loss": sum(i.points_scored for i in players) / (
                    len([g for g, p in zip(games, players) if g.winning_team_id != p.team_id]) or 1),
            "Aces per Game": sum(i.aces_scored for i in players) / games_played,
            "Faults per Game": sum(i.faults for i in players) / games_played,
            "Cards": sum(i.green_cards + i.yellow_cards + i.red_cards for i in players),
            "Cards per Game": sum(i.green_cards + i.yellow_cards + i.red_cards for i in players) / games_played,
            "Points per Card": sum(i.points_scored for i in players) / (
                    sum(i.green_cards + i.yellow_cards + i.red_cards for i in players) or 1),
            "Serves per Game": sum(i.served_points for i in players) / games_played,
            "Serves per Ace": sum(i.served_points for i in players) / (sum(i.aces_scored for i in players) or 1),
            "Serves per Fault": sum(i.served_points for i in players) / (sum(i.faults for i in players) or 1),
            "Serve Ace Rate": sum(i.aces_scored for i in players) / (
                    sum(i.served_points for i in players) or 1),
            "Serve Fault Rate": sum(i.faults for i in players) / (
                    sum(i.served_points for i in players) or 1),
            "Percentage of Points Scored": sum(i.points_scored for i in players) / (
                    sum(i.rounds_on_court + i.rounds_carded for i in players) or 1),
            "Percentage of Points Scored For Team": sum(i.points_scored for i in players) / (sum(
                g.team_one_score if g.team_one_id == p.team_id else g.team_two_score for g, p in
                zip(games, players)) or 1),
            "Percentage of Games Starting Left": len([i for i in players if i.start_side == 'Left']) / games_played,
            "Percentage of Points Served Won": sum(i.served_points_won for i in players) / (
                    sum(i.served_points for i in players) or 1),
            "Serves Received": sum(i.serves_received for i in players),
            "Serves Returned": sum(i.serves_returned for i in players),
            "Max Serve Streak": max([i.serve_streak for i in players] + [0]),
            "Average Serve Streak": sum(i.serve_streak for i in players) / games_played,
            "Max Ace Streak": max([i.ace_streak for i in players] + [0]),
            "Average Ace Streak": sum(i.ace_streak for i in players) / games_played,
            "Serve Return Rate": sum(i.serves_returned for i in players) / (
                    sum(i.serves_received for i in players) or 1),
            "Votes per 100 games": 100 * len([i for i in games if i.best_player_id == self.id]) / games_played,
        }
        if admin:
            ret["Penalty Points"] = ret["Green Cards"] * 2 + ret["Yellow Cards"] * 5 + ret["Red Cards"] * 10
            ret["Warnings"] = sum(i.warnings for i in players)
        if make_nice:
            for k, v in ret.items():
                if k in PERCENTAGES:
                    ret[k] = f"{100.0 * v: .2f}%".strip()
                elif isinstance(v, float):
                    ret[k] = round(v, 2)
        return ret

    def played_in_tournament(self, tournament_searchable_name):
        if not tournament_searchable_name:
            return True
        from database.models import PlayerGameStats
        from database.models import Tournaments
        tournament_id = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable_name).first().id
        return bool(PlayerGameStats.query.filter(PlayerGameStats.player_id == self.id,
                                                 PlayerGameStats.tournament_id == tournament_id).first())

    def as_dict(self, include_stats=False, tournament=None, admin_view=False, make_nice=False):
        from database.models import PlayerGameStats
        d = {
            "name": self.name,
            "searchableName": self.searchable_name,
            "imageUrl": self.image_url if not self.image_url.startswith("/") else "https://squarers.org" + self.image_url,
        }
        if include_stats:
            game_filter = (lambda a: a.filter(PlayerGameStats.tournament_id == tournament)) if tournament else None
            d["stats"] = self.stats(game_filter, make_nice=make_nice, admin=admin_view)
        if admin_view:
            d |= {
                "isAdmin": self.is_admin
            }
        return d