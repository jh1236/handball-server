from FixtureGenerators.FixturesGenerator import FixturesGenerator
from database.models import Tournaments, Games
from structure import manage_game


# [sf1, sf2], [3v3, 4v4, 5v5]
# [sf1, 3v3, sf2, 4v4, 5v5]

class PooledFinals(FixturesGenerator):
    def _end_of_round(self, tournament_id):
        pool_one, pool_two = Tournaments.query.filter(Tournaments.id == tournament_id).first().ladder()
        finals_games = Games.query.filter(Games.id == tournament_id, Games.is_final == True).all()
        last_game = Games.query.filter(Games.id == tournament_id).order_by(Games.round.desc).first()[-1]

        if len(finals_games) > 2:
            self.end_tournament()
        elif finals_games:
            manage_game.create_game(tournament_id, finals_games[0].losing_team_id, finals_games[1].losing_team_id,
                                    is_final=True,
                                    round_number=finals_games[-1].round_number + 1)
            manage_game.create_game(tournament_id, finals_games[0].winning_team_id, finals_games[1].winning_team_id,
                                    is_final=True,
                                    round_number=finals_games[-1].round_number + 1)
        else:
            manage_game.create_game(tournament_id, pool_one[0].id, pool_two[1].id, is_final=True,
                                    round_number=last_game.round_number + 1)
            manage_game.create_game(tournament_id, pool_two[0].id, pool_one[1].id, is_final=True,
                                    round_number=last_game.round_number + 1)
