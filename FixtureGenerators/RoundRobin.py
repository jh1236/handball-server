from FixtureGenerators.FixturesGenerator import FixturesGenerator
from database import db
from database.models import Tournaments, TournamentTeams, Games
from structure import manage_game


class RoundRobin(FixturesGenerator):
    def __init__(self, tournament):

        super().__init__(tournament, fill_officials=True, editable=False, fill_courts=True)

    def _end_of_round(self, tournament_id):

        teams = [i.team for i in TournamentTeams.query.filter(TournamentTeams.tournament_id == tournament_id).all()]
        last_game = Games.query.filter(Games.tournament_id == tournament_id).order_by(Games.round.desc()).first()
        rounds = (last_game.round if last_game else 0) + 1

        if len(teams) % 2 != 0:  # if there is an odd number of teams, add a bye.
            teams += [1]

        if len(teams) <= rounds:
            Tournaments.query.filter(Tournaments.id == tournament_id).first().in_finals = True
            db.session.commit()
            return


        for _ in range(rounds - 1):
            # Rotate the teams except the first one
            teams[1:] = [teams[-1]] + teams[1:-1]

        mid = len(teams) // 2
        for j in range(mid):
            team_one = teams[j]
            team_two = teams[len(teams) - 1 - j]
            manage_game.create_game(tournament_id, team_one, team_two, round_number=rounds)
