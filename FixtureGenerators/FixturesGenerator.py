from collections import defaultdict
from itertools import zip_longest
from math import ceil

from database import db
from database.models import Games, PlayerGameStats, TournamentOfficials, Tournaments
from utils.logging_handler import logger


# from database.models import Tournaments
# from database import db

class FixturesGenerator:

    def __init__(self, tournament_id, *, fill_officials, editable, fill_courts):
        self.tournament_id = tournament_id
        self.editable = editable
        self.fill_officials = fill_officials
        self.fill_courts = fill_courts

    def manual_allowed(self):
        return self.editable

    def _end_of_round(self, tournament):
        raise NotImplementedError()

    def _begin_tournament(self, tournament_id):
        pass

    def end_of_round(self):
        self._end_of_round(self.tournament_id)
        if self.fill_courts:
            self.add_courts()
        if self.fill_officials:
            self.add_umpires()

    def add_courts(self):
        rounds = Games.query.filter(Games.tournament_id == self.tournament_id).order_by(
            Games.round.desc()).first().round
        games = Games.query.filter(Games.tournament_id == self.tournament_id, Games.round == rounds,
                                   Games.is_bye == False, Games.started == False, Games.is_final == False).all()
        finals = Games.query.filter(Games.tournament_id == self.tournament_id, Games.round == rounds,
                                    Games.is_bye == False, Games.started == False, Games.is_final == True).all()

        l = ceil(len(games) / 2) - 1
        f = Games.tournament_id == self.tournament_id
        games.sort(key=lambda x: x.team_one.stats(f)["Games Won"] + x.team_two.stats(f)["Games Won"], reverse=True)
        for i, g in enumerate(games):
            g.court = i > l
        for g in finals:
            g.court = 0
        db.session.commit()

    def begin_tournament(self):
        self._begin_tournament(self.tournament_id)
        self.end_of_round()

    def end_tournament(self,
                       note="Thank you for participating in the tournament! We look forward to seeing you next time"):
        """i wanted to automate this but i couldn't get it to work, either with SQLAlchemy or sqlite"""

        tournament = Tournaments.query.filter(Tournaments.id == self.tournament_id).first()
        tournament.finished = True
        tournament.notes = note
        db.session.commit()

    def add_umpires(self):
        from database.models import Tournaments # WHAT THE FUCK?! i dont know what is going on here, but this fixes it?!
        games_query = Games.query.filter(Games.tournament_id == self.tournament_id, Games.is_bye == False).order_by(
            Games.id).all()
        players = PlayerGameStats.query.join(Games, Games.id == PlayerGameStats.game_id).filter(
            PlayerGameStats.tournament_id == self.tournament_id, Games.is_bye == False).all()
        logger.fatal(Tournaments.__dict__)
        logger.fatal(Games.__dict__)
        tourney = Tournaments.query.filter(Tournaments.id == self.tournament_id).first()
        officials = TournamentOfficials.query.filter(TournamentOfficials.tournament_id == self.tournament_id).all()

        rounds = defaultdict(list)
        game_to_players = defaultdict(list)
        for i in players:
            game_to_players[i.game_id].append(i)
        for i in games_query:
            rounds[i.round].append(i)
        rounds = list(rounds.values())
        # id, round, court, official
        for r in rounds:
            court_one_games = [i for i in r if i.court == 0]
            court_two_games = [i for i in r if i.court == 1]
            for games in zip_longest(court_one_games, court_two_games):
                for g in games:
                    court_one_officials: list[TournamentOfficials] = sorted(
                        officials,
                        key=lambda it: (
                            -it.official.proficiency,
                            it.games_umpired,
                            it.court_one_umpired,
                        ),
                    )
                    print([(i.official.person.name, i.games_umpired,) for i in court_one_officials])
                    court_two_officials: list[TournamentOfficials] = sorted(
                        officials,
                        key=lambda it: (
                            3 if (it.official.proficiency == 0) else it.official.proficiency,
                            it.games_umpired,
                            -it.court_one_umpired,
                        ),
                    )
                    logger.info(
                        f"c1: {[(i.official.person_id, i.official.proficiency) for i in court_one_officials]}, "
                        f"c2: {[(i.official.person_id, i.official.proficiency) for i in court_two_officials]}"
                    )
                    #  games.id, round, court, official, scorer, [players]

                    if not g:
                        continue
                    if g.official_id:
                        continue
                    for o in court_one_officials if g.court == 0 else court_two_officials:
                        if o.official_id in [k.official_id for k in games if k]:
                            # the official is already umpiring this round
                            continue
                        if any([o.official.person_id in [j.player_id for j in game_to_players[i.id]] for i in games if
                                i]):
                            # the official is playing this round
                            continue
                        g.official_id = o.official_id
                        db.session.commit()
                        break
            if not tourney.has_scorer:
                continue
            for games in zip_longest(court_one_games, court_two_games):
                for g in games:
                    if not g:
                        continue
                    if g.scorer_id:
                        continue
                    scorer = sorted(
                        officials,
                        key=lambda it: (
                            it.official.proficiency == 0,
                            it.games_umpired,
                            it.games_scored
                        ),
                    )
                    print(f"{[(i.official.person_id, i.official.proficiency) for i in scorer]}")
                    for o in scorer:
                        if o.official_id in [k.official_id for k in games if k]:
                            # the official is umpiring this round
                            continue
                        if o.official_id in [k.scorer_id for k in games if k]:
                            # the official is already scoring this round
                            continue
                        if any([o.official.person_id in [j.player_id for j in game_to_players[i.id]] for i in games if
                                i]):
                            # the official is playing this round
                            continue
                        g.scorer_id = o.official_id
                        db.session.commit()
                        break
                    if not g.scorer_id:
                        # there was no scorer found, set the scorer to be equal to the umpire
                        g.scorer_id = g.official_id
                        db.session.commit()

        db.session.commit()


def get_type_from_name(name: str, tournament: int) -> FixturesGenerator:
    from FixtureGenerators.BasicFinals import BasicFinals
    from FixtureGenerators.OneRound import OneRound
    from FixtureGenerators.Pooled import Pooled
    from FixtureGenerators.RoundRobin import RoundRobin
    from FixtureGenerators.Swiss import Swiss
    from FixtureGenerators.TopThreeFinals import TopThreeFinals
    return {
        "BasicFinals": BasicFinals(tournament),
        "Pooled": Pooled(tournament),
        "RoundRobin": RoundRobin(tournament),
        "OneRoundEditable": OneRound(tournament),
        "Swiss": Swiss(tournament),
        "TopThreeFinals": TopThreeFinals(tournament)
    }[name]
