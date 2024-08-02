from database import db
from database.models import *
from start import app
from structure import manage_game
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


def sync_all_games():
    games = Games.query.all()
    for i in games:
        if i.is_bye: continue
        if i.id % 20 == 0:
            print(f"Syncing Game {i.id}")
        try:
            manage_game.sync(i.id)
        except Exception as e:
            print(e.args)
            print(f"Game {i.id} failed to sync")
    db.session.commit()


def interpolate_start_times():
    games = Games.query.filter(Games.tournament_id == 1, Games.id <= 342).all()
    first_ever_game = 1690887600
    last_time_stamp = 1709901482.6885524
    time_per_event = 29.718165623703534
    current_start_time = 0
    prev_round = 0
    for i in games:
        print(i.id)
        if i.round != prev_round:
            prev_round = i.round
            # linearly interpolate the two start times
            current_start_time = first_ever_game + ((i.round - 1) / 32) * (last_time_stamp - first_ever_game)
        length = len(GameEvents.query.filter(GameEvents.game_id == i.id).all()) * time_per_event
        i.start_time = current_start_time
        i.length = length
        current_start_time += length + 300
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        print(Teams.query.filter(Teams.searchable_name == "bedwars_besties").first().stats())