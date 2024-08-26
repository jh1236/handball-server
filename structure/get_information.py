from database.models import Tournaments

tournament_id = {}


def get_tournament_id(searchable_name) -> int:
    if not searchable_name:
        return None
    if searchable_name in tournament_id:
        return tournament_id[searchable_name]
    out = Tournaments.query.filter(Tournaments.searchable_name == searchable_name).first().id
    tournament_id[searchable_name] = out
    return out
