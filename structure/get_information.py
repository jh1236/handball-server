from utils.databaseManager import DatabaseManager

game_and_side = {}

tournament_id = {}


def get_team_id_from_game_and_side(game_id, first_team, c=None) -> int:
    if game_id in game_and_side:
        return game_and_side[game_id][not first_team]
    if not c:
        with DatabaseManager() as c:
            if first_team:
                team = c.execute("""SELECT teamOne FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
            else:
                team = c.execute("""SELECT teamTwo FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
            return team
    else:
        if first_team:
            team = c.execute("""SELECT teamOne FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
        else:
            team = c.execute("""SELECT teamTwo FROM games WHERE games.id = ?""", (game_id,)).fetchone()[0]
        return team


def get_tournament_id(searchable_name, c=None) -> int:
    if searchable_name in tournament_id:
        return tournament_id[searchable_name]
    if not c:
        with DatabaseManager() as c:
            out = c.execute("SELECT id FROM tournaments WHERE searchableName=?", (searchable_name,)).fetchone()
        if out:
            out = out[0]
        return out
    else:
        out = c.execute("SELECT id FROM tournaments WHERE searchableName=?", (searchable_name,)).fetchone()
        if out:
            out = out[0]
        return out
