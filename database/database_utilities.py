from database.models import PlayerGameStats, GameEvents


def on_court_for_game(game_id, team_id,event=None) -> list[PlayerGameStats]:
    game = event or GameEvents.query.filter((GameEvents.game_id == game_id)).order_by(GameEvents.id.desc()).first()
    players = PlayerGameStats.query.filter(
        (game.team_one_left_id == PlayerGameStats.player_id)
        | (game.team_one_right_id == PlayerGameStats.player_id)
        | (game.team_two_right_id == PlayerGameStats.player_id)
        | (game.team_two_left_id == PlayerGameStats.player_id)).filter(
        (PlayerGameStats.game_id == game_id))
    if team_id:
        players = players.filter(PlayerGameStats.team_id == team_id)
    return players.all()
