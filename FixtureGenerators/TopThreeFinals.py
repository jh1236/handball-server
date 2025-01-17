from FixtureGenerators.FixturesGenerator import FixturesGenerator
from database.models import Games, Tournaments
from structure import manage_game


class TopThreeFinals(FixturesGenerator):

    def __init__(self, tournament_id):
        super().__init__(tournament_id, fill_officials=True, editable=False, fill_courts=True)
        self.top_team = None

    def _end_of_round(self, tournament_id):
        tournament = Tournaments.query.filter(Tournaments.id == tournament_id).first()
        ladder = tournament.ladder()
        finals_games = Games.query.filter(Games.id == tournament_id, Games.is_final == True).all()
        last_game = Games.query.filter(Games.id == tournament_id).order_by(Games.round.desc).first()[-1]
        if len(finals_games) > 2:
            self.end_tournament()
        elif finals_games:
            manage_game.create_game(tournament_id, finals_games[0].losing_team_id, finals_games[1].losing_team_id, is_final=True,
                                    round_number=finals_games[-1].round_number + 1)
            manage_game.create_game(tournament_id, finals_games[0].winning_team_id, finals_games[1].winning_team_id, is_final=True,
                                    round_number=finals_games[-1].round_number + 1)
        else:
            manage_game.create_game(tournament_id, ladder[0][0].id, ladder[3][0].id, is_final=True, round_number=last_game.round_number + 1)
            manage_game.create_game(tournament_id, ladder[1][0].id, ladder[2][0].id, is_final=True, round_number=last_game.round_number + 1)

        