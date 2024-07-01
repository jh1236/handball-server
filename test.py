from database import db
from database.models import *
from start import app
from utils.statistics import calc_elo


def regen_elo():
    EloChange.query.delete()
    games = Games.query.all()
    for game in games:
        if not game.ranked or game.is_final or game.is_bye: continue

        team_one = PlayerGameStats.query.filter(PlayerGameStats.team_id == game.team_one_id,
                                                PlayerGameStats.game_id == game.id)

        team_two = PlayerGameStats.query.filter(PlayerGameStats.team_id == game.team_two_id,
                                                PlayerGameStats.game_id == game.id)
        if not GameEvents.query.filter(GameEvents.game_id == game.id, GameEvents.event_type == 'Forfeit').all():
            team_one.filter((PlayerGameStats.rounds_on_court + PlayerGameStats.rounds_carded) > 0)
            team_two.filter((PlayerGameStats.rounds_on_court + PlayerGameStats.rounds_carded) > 0)
        team_one = team_one.all()
        team_two = team_two.all()
        print(f"{game.team_two.name} vs {game.team_one.name}")
        teams = [team_one, team_two]
        elos = [0, 0]
        for i, v in enumerate(teams):
            elos[i] = sum(j.player.elo() for j in v)
            elos[i] /= len(v)

        print(elos)
        for i in teams:
            my_team = i != teams[0]
            win = game.winning_team_id == i[0].team_id
            for j in i:
                player_id = j.player_id
                elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
                add = EloChange(game_id=game.id, player_id=player_id, tournament_id=game.tournament_id,
                                elo_delta=elo_delta)
                db.session.add(add)
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        regen_elo()
