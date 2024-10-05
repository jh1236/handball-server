import re
import time

from FixtureGenerators.FixturesGenerator import get_type_from_name
from database import db
from database.database_utilities import on_court_for_game
from database.models import *
from utils.statistics import calc_elo
from utils.logging_handler import logger

SIDES = ["Left", "Right", "Substitute"]


def searchable_of(name: str):
    s = name.lower().replace(" ", "_").replace(",", "").replace("the_", "")
    return re.sub("[^a-zA-Z0-9_]", "", s)


def pgs_from_game_and_player(game_id, person_id):
    return PlayerGameStats.query.filter_by(game_id=game_id, player_id=person_id).first()


def sync(game_id):
    game: Games = Games.query.filter(Games.id == game_id).first()
    game.reset()
    events: list[GameEvents] = GameEvents.query.filter_by(game_id=game_id).order_by(GameEvents.id).all()
    all_players: list[PlayerGameStats] = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
    fault = False
    streak = 1
    ace_streak = 0
    # HACK: make this not hardcoded
    carry_over_cards = game.tournament_id >= 8
    for i in all_players:
        i.reset_stats()
        prev_game_player = PlayerGameStats.query.filter(PlayerGameStats.player_id == i.player_id,
                                                        PlayerGameStats.tournament_id == i.tournament_id,
                                                        PlayerGameStats.team_id == i.team_id,
                                                        PlayerGameStats.game_id < i.game_id).order_by(
            PlayerGameStats.game_id.desc()).first()
        if prev_game_player and carry_over_cards:
            card_time_left = max(prev_game_player.card_time_remaining, 0) if not prev_game_player.red_cards else -1
            card_time = max(prev_game_player.card_time, 0) if not prev_game_player.red_cards else -1
        else:
            card_time = 0
            card_time_left = 0
        i.card_time_remaining = card_time_left
        i.card_time = card_time
    i = None
    for c, i in enumerate(events):
        players_on_court = on_court_for_game(game_id, None, event=i)
        is_team_one = i.team_id == game.team_one_id
        player: PlayerGameStats = ([j for j in all_players if j.player_id == i.player_id] + [None])[0]
        left_served = i.side_to_serve == 'Left'
        non_serving_team = [i.team_one_left, i.team_one_right] if i.team_who_served_id != game.team_one_id else [
            i.team_two_left, i.team_two_right]
        match i.event_type:
            case "Score":
                prev_event = events[c - 1].event_type
                fault = False
                if player is not None:
                    player.points_scored += 1
                    player_who_served = [j for j in all_players if j.player_id == i.player_who_served_id][0]
                    player_who_served.served_points += 1
                    if player_who_served.team_id == i.team_id:
                        player_who_served.served_points_won += 1
                    receiving_player = non_serving_team[not left_served]
                    if not receiving_player:
                        receiving_player = [i for i in non_serving_team if i][0]
                    else:
                        receiving_pgs = pgs_from_game_and_player(game_id, receiving_player.id)
                        if receiving_pgs and receiving_pgs.card_time_remaining != 0:
                            receiving_player = ([i for i in non_serving_team if i and
                                                 pgs_from_game_and_player(game_id, i.id).card_time_remaining == 0] + [
                                                    None])[0]
                    if receiving_player:
                        receiving_pgs = pgs_from_game_and_player(game_id, receiving_player.id)
                        if receiving_pgs and receiving_pgs.player_id and (
                                i.notes != 'Penalty' or prev_event == 'Ace'):
                            receiving_pgs.serves_received += 1
                            if prev_event != 'Ace':
                                receiving_pgs.serves_returned += 1
                    if player_who_served.player_id == i.player_to_serve_id:
                        streak += 1
                        if player_who_served.serve_streak < streak:
                            player_who_served.serve_streak = streak
                    else:
                        streak = 1
                else:
                    ace_streak = 0
                if is_team_one:
                    game.team_one_score += 1
                else:
                    game.team_two_score += 1
                for j in players_on_court:
                    if j.card_time_remaining == 0:
                        j.rounds_on_court += 1
                    else:
                        j.rounds_carded += 1
                        if j.card_time_remaining > 0:
                            j.card_time_remaining -= 1

            case "Pardon":
                player.card_time_remaining = 0
            case "Ace":
                player.aces_scored += 1
                player_who_served = [j for j in all_players if j.player_id == i.player_who_served_id][0]
                if player_who_served.player_id == i.player_to_serve_id:
                    ace_streak += 1
                    if player_who_served.ace_streak < ace_streak:
                        player_who_served.ace_streak = ace_streak
                else:
                    ace_streak = 0
            case "Fault":
                player.faults += 1
                player.served_points += 1
                if fault:
                    player.double_faults += 1
                    fault = False
                else:
                    fault = True
            case "Green Card":
                player.green_cards += 1
                if player.card_time_remaining >= 0:
                    player.card_time_remaining += i.details
                    player.card_time = player.card_time_remaining
            case "Warning":
                player.warnings += 1
            case "Yellow Card":
                player.yellow_cards += 1
                if player.card_time_remaining >= 0:
                    player.card_time_remaining += i.details
                    player.card_time = player.card_time_remaining
            case "Red Card":
                player.red_cards += 1
                player.card_time_remaining = -1
                player.card_time = -1
            case "Timeout":
                if is_team_one:
                    game.team_one_timeouts += 1
                else:
                    game.team_two_timeouts += 1
            case "Substitute":
                pass
            case "Forfeit":
                if is_team_one:
                    game.team_two_score = max(game.team_one_score + 2, 11)
                else:
                    game.team_one_score = max(game.team_two_score + 2, 11)
            case "Resolve":
                game.resolved = True
            case "Protest":
                game.protested = True
            case "End Game":
                game.best_player_id = i.details
                if i.details:
                    PlayerGameStats.query.filter(PlayerGameStats.player_id == i.details,
                                                 PlayerGameStats.game_id == game_id).first().is_best_player = 1
                game.notes = i.notes
                game.ended = True
            case "Start":
                game.started = True
            case _:
                pass

    if max(game.team_two_score, game.team_one_score) >= 11 and abs(game.team_two_score - game.team_one_score) >= 2:
        game.someone_has_won = True
        game.winning_team_id = game.team_one_id if game.team_one_score > game.team_two_score else game.team_two_id
    if i:  # cursed python, i will always be the last
        game.player_to_serve_id = i.player_to_serve_id
        game.team_to_serve_id = i.team_to_serve_id
        game.side_to_serve = i.side_to_serve


def game_string_lookup(char: str):
    d = {
        "s": "Score",
        "a": "Ace",
        "g": "Green Card",
        "y": "Yellow Card",
        "v": "Red Card",
        "f": "Fault",
        "t": "Timeout",
        "x": "Substitute",
        "e": "Forfeit"
    }
    if char in d:
        return d[char]
    if char.isdigit():
        return "Yellow Card"
    return None


def _team_and_position_to_id(game_id, first_team, left_player, c) -> int:
    game = GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first()

    if first_team:
        left = game.team_one_left_id
        right = game.team_one_right_id or left
        return [right, left][left_player]
    else:
        left = game.team_two_left_id
        right = game.team_two_right_id or left
        return [right, left][left_player]


def _tournament_from_game(game_id, c):
    return Games.query.filter(Games.id == game_id).first().tournament_id


def game_is_over(game_id):
    return Games.query.filter(Games.id == game_id).first().someone_has_won


def game_is_ended(game_id):
    return Games.query.filter(Games.id == game_id).first().ended


def game_has_started(game_id):
    return Games.query.filter(Games.id == game_id).first().started


def _score_point(game_id, first_team, left_player, penalty=False, points=1):
    for _ in range(points):
        _add_to_game(game_id, "Score", first_team, left_player, team_to_serve=first_team,
                     notes="Penalty" if penalty else None)


def get_serve_details(game, team_one, team_two, team_who_served, player_who_served, next_team_to_serve, serve_side):
    serve_team = team_one if next_team_to_serve == game.team_one_id else team_two
    if not game.tournament.badminton_serves:
        if team_who_served != next_team_to_serve:
            last_time_served = GameEvents.query.filter(
                (GameEvents.game_id == game.id) & (GameEvents.team_who_served_id == next_team_to_serve)).order_by(
                GameEvents.id.desc()).first()
            if not last_time_served:
                next_serve_side = 'Left'
                next_player_to_serve = team_one[0] if next_team_to_serve == game.team_one_id else team_two[0]
            else:
                next_serve_side = 'Right' if last_time_served.side_served == 'Left' else 'Left'
                new_right = next_serve_side == 'Right'
                next_player_to_serve = team_one[new_right] if next_team_to_serve == game.team_one_id else team_two[
                    new_right]
        else:
            next_serve_side = serve_side
            next_player_to_serve = serve_team[next_serve_side == 'Right']
    else:
        if team_who_served == next_team_to_serve:
            # ABSOLUTELY EVIL HACK
            # THEY CAN NOT GIVE ME ACCESS TO MUTABLE ARRAYS
            serve_team[0], serve_team[1] = serve_team[1], serve_team[0]
            next_serve_side = 'Right' if serve_side == 'Left' else 'Left'
            next_player_to_serve = serve_team[next_serve_side == 'Right']
        else:
            last_time_served = GameEvents.query.filter(
                (GameEvents.game_id == game.id) & (GameEvents.team_who_served_id == next_team_to_serve)).order_by(
                GameEvents.id.desc()).first()
            if last_time_served:
                next_serve_side = 'Right' if last_time_served.side_served == 'Left' else 'Left'
                next_player_to_serve = \
                    ([i for i in serve_team if i and i.id != last_time_served.player_who_served_id] + [None])[0]
                if next_player_to_serve == None:
                    next_player_to_serve = [i for i in serve_team if i][0]
            else:
                next_serve_side = 'Left'
                next_player_to_serve = serve_team[0]
    return next_player_to_serve, next_serve_side


def _add_to_game(game_id, char: str, first_team, left_player, team_to_serve=None, details=None, notes=None):
    game = Games.query.filter(Games.id == game_id).first()
    if first_team is not None:
        team = Teams.query.filter(Teams.id == (game.team_one_id if first_team else game.team_two_id)).first()
    else:
        team = None
    last_game_event = GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first()
    player: PlayerGameStats | None
    if left_player is None:
        player = None
    else:
        if first_team:
            player = last_game_event.team_one_left if left_player else last_game_event.team_one_right
        else:
            player = last_game_event.team_two_left if left_player else last_game_event.team_two_right

    next_team_to_serve = None if team_to_serve is None else Teams.query.filter(
        Teams.id == (game.team_one_id if team_to_serve else game.team_two_id)).first().id
    players = on_court_for_game(game_id, None)
    team_who_served = last_game_event.team_to_serve_id
    player_who_served = last_game_event.player_to_serve
    serve_side = last_game_event.side_to_serve or 'Left'
    next_team_to_serve = next_team_to_serve or team_who_served
    team_one = [last_game_event.team_one_left, last_game_event.team_one_right]
    team_two = [last_game_event.team_two_left, last_game_event.team_two_right]
    if char == "Substitute":
        all_players = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
        player_on = [i for i in all_players if i.id not in [j.id for j in players] and i.team_id == team.id][0]
        if first_team:
            team_one[not left_player] = player_on.player
        else:
            team_two[not left_player] = player_on.player
    if char == 'Score':
        next_player_to_serve, next_serve_side = get_serve_details(game, team_one, team_two, team_who_served,
                                                                  player_who_served, next_team_to_serve, serve_side)
        if next_player_to_serve is None:
            next_player_to_serve = \
                [i for i in (team_one if next_team_to_serve == game.team_one_id else team_two) if i and
                 pgs_from_game_and_player(game_id, i.id).card_time_remaining == 0][0]
    else:
        next_serve_side = serve_side
        serve_team = team_one if next_team_to_serve == game.team_one_id else team_two
        next_player_to_serve = serve_team[next_serve_side == 'Right']

    team_id = team.id if team is not None else None
    player_id = player.id if player is not None else None
    player_who_served_id = player_who_served.id if player_who_served is not None else None
    next_player_to_serve_id = next_player_to_serve.id if next_player_to_serve is not None else None
    team_ids = [i.id if i else None for i in team_one + team_two]
    to_add = GameEvents(game_id=game.id, tournament_id=game.tournament_id, event_type=char,
                        details=details, notes=notes, team_id=team_id, player_id=player_id,
                        team_who_served_id=team_who_served, player_who_served_id=player_who_served_id,
                        side_served=serve_side,
                        team_to_serve_id=next_team_to_serve, player_to_serve_id=next_player_to_serve_id,
                        side_to_serve=next_serve_side,
                        team_one_left_id=team_ids[0],
                        team_one_right_id=team_ids[1],
                        team_two_left_id=team_ids[2],
                        team_two_right_id=team_ids[3])
    db.session.add(to_add)

    sync(game_id)
    server = PlayerGameStats.query.filter(PlayerGameStats.player_id == game.player_to_serve_id,
                                          PlayerGameStats.game_id == game.id).first()
    server_team_players_on_court = [i.player_id for i in players if
                                    i.team_id == to_add.team_to_serve_id and i.card_time_remaining == 0]
    if server and server.card_time_remaining != 0 and server_team_players_on_court:
        to_add.player_to_serve_id = server_team_players_on_court[0]
        sync(game_id)
    db.session.commit()


def start_game(game_id, swap_service, team_one, team_two, team_one_iga, official=None, scorer=None):
    if game_has_started(game_id):
        raise ValueError("Game is Already Over!")
    game = Games.query.filter(Games.id == game_id).first()
    team_one_id, team_two_id = game.team_one, game.team_two

    if team_one is None:
        team_one = [i.player_id for i in PlayerGameStats.query.filter(
            (PlayerGameStats.game_id == game.id) & (PlayerGameStats.team_id == team_one_id)).all()]
    else:
        team_one = [People.query.filter(People.searchable_name == i).first().id for i in team_one]
    if team_two is None:
        team_two = [i.searchable_name for i in PlayerGameStats.query.filter(
            (PlayerGameStats.game_id == game.id) & (PlayerGameStats.team_id == team_two_id)).all()]
    else:
        team_two = [People.query.filter(People.searchable_name == i).first().id for i in team_two]

    # I just wanna see how this works
    team_one += team_one[0:1]
    team_two += team_two[0:1]
    iga = team_one_id if team_one_iga else team_two_id
    game.status = 'In Progress'
    game.admin_status = 'In Progress'
    game.noteable_status = 'In Progress'
    game.iga_side = iga
    game.start_time = time.time()
    if official:
        person_id = People.query.filter(People.searchable_name == official).first().id
        game.official_id = Officials.query.filter(Officials.person_id == person_id).first().id
    if scorer:
        person_id = People.query.filter(People.searchable_name == scorer).first().id
        game.official_id = Officials.query.filter(Officials.person.searchable_name == person_id).first().id
    for id, side in zip(team_one, SIDES):
        if not id: continue
        PlayerGameStats.query.filter(PlayerGameStats.id == id).first().start_side = side
    for id, side in zip(team_two, SIDES):
        if not id: continue
        PlayerGameStats.query.filter(PlayerGameStats.id == id).first().start_side = side
    serving_team = game.team_two if swap_service else game.team_one
    to_add = GameEvents(game_id=game.id, tournament_id=game.tournament_id, event_type="Start", side_to_serve='Left',
                        team_to_serve_id=serving_team.id,
                        player_to_serve_id=team_two[0] if swap_service else team_one[0],
                        team_one_left_id=team_one[0], team_two_left_id=team_two[0],
                        team_one_right_id=team_one[1], team_two_right_id=team_two[1])
    db.session.add(to_add)
    sync(game_id)
    if pgs_from_game_and_player(game_id, to_add.player_to_serve_id).card_time_remaining != 0:
        to_add.player_to_serve_id = team_two[1] if swap_service else team_one[1]
    db.session.commit()


def score_point(game_id, first_team, left_player):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _score_point(game_id, first_team, left_player)
    db.session.commit()


def ace(game_id):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    game = Games.query.filter(game_id == Games.id).first()
    first_team = bool(game.team_one == game.team_to_serve)
    last_game_event = GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first()
    left_player = bool(
        last_game_event.player_to_serve_id == last_game_event.team_one_left_id if first_team else last_game_event.team_two_left_id)
    _add_to_game(game_id, "Ace", first_team, left_player)
    _score_point(game_id, first_team, left_player, penalty=True)
    db.session.commit()


def fault(game_id):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    game = Games.query.filter(game_id == Games.id).first()
    first_team = bool(game.team_one == game.team_to_serve)
    last_game_event = GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first()
    left_player = bool(
        last_game_event.player_to_serve_id == last_game_event.team_one_left_id if first_team else last_game_event.team_two_left_id)
    prev_event = GameEvents.query.filter(GameEvents.game_id == game_id, (GameEvents.event_type == 'Fault') | (
            GameEvents.event_type == 'Score')).order_by(GameEvents.id.desc()).first()
    if prev_event:
        prev_event = prev_event.event_type
    _add_to_game(game_id, "Fault", first_team, left_player)
    if prev_event == "Fault":
        _score_point(game_id, not first_team, None, penalty=True)
    db.session.commit()


def card(game_id, first_team, left_player, color, duration, reason):
    game = Games.query.filter(Games.id == game_id).first()
    if color in ["Green", "Yellow", "Red"]:
        color += " Card"
    _add_to_game(game_id, color, first_team, left_player, notes=reason, details=int(duration))
    team = game.team_one if first_team else game.team_two
    players = on_court_for_game(game_id, team.id)
    both_carded = min([i.card_time_remaining if i.card_time_remaining >= 0 else 12 for i in players])
    if both_carded != 0:
        my_score = game.team_one_score
        their_score = game.team_two_score
        if game.someone_has_won:
            return
        if not first_team:
            my_score, their_score = their_score, my_score
        both_carded = min(both_carded, max(11 - their_score, my_score + 2 - their_score))
        _score_point(game_id, not first_team, None, penalty=True, points=both_carded)
    db.session.commit()


def undo(game_id):
    if game_is_ended(game_id):
        raise ValueError("Game is Already Over!")
    delete_after = GameEvents.query.filter(GameEvents.game_id == game_id,
                                           (GameEvents.notes == None) | (GameEvents.notes != 'Penalty'),
                                           GameEvents.event_type != 'End Timeout',
                                           GameEvents.event_type != 'Protest').order_by(GameEvents.id.desc()).first().id
    GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.id >= delete_after).delete()
    sync(game_id)
    db.session.commit()


def change_code(game_id):
    if game_id <= 0:
        game = Games.query.filter(Games.court == abs(game_id), Games.started).order_by(Games.id.desc()).first()
        game_id = game.id
    else:
        game = Games.query.filter(Games.id == game_id).first()
    if game is None:
        return 1
    ge = GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first()
    return (game_id if not ge else ge.id +
                                   (get_serve_timer(game_id) > 0))


def time_out(game_id, first_team):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "Timeout", first_team, None)
    db.session.commit()


def forfeit(game_id, first_team):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "Forfeit", first_team, None)
    db.session.commit()


def end_timeout(game_id):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "End Timeout", None, None)
    db.session.commit()


def end_game(game_id, best_player, notes, protest_team_one, protest_team_two):
    if not game_is_over(game_id):
        raise ValueError("Game is not yet Over!")
    game = Games.query.filter(Games.id == game_id).first()
    best = People.query.filter(People.searchable_name == best_player).first()
    players = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
    forfeit = GameEvents.query.filter(GameEvents.event_type == 'Forfeit', GameEvents.game_id == game_id).first()
    if best is None:
        teams = [game.team_one, game.team_two]
        if forfeit is None and [i for i in teams if i.non_captain_id]:
            raise ValueError("Best Player was not provided")

    if protest_team_one:
        _add_to_game(game_id, "Protest", True, None, notes=protest_team_one)
    if protest_team_two:
        _add_to_game(game_id, "Protest", False, None, notes=protest_team_two)
    _add_to_game(game_id, "End Game", None, None, notes=notes, details=best.id if best else None)

    if any(i.red_cards for i in players):
        game.admin_status = 'Red Card Awarded'
    elif protest_team_one or protest_team_two:
        game.admin_status = 'Protested'
    elif notes.strip():
        game.admin_status = 'Notes to Review'
    elif any(i.yellow_cards for i in players):
        game.admin_status = 'Yellow Card Awarded'
    elif forfeit:
        game.admin_status = 'Forfeit'
    else:
        game.admin_status = 'Official'
    game.noteable_status = game.admin_status

    game.status = 'Official'
    game.length = time.time() - game.start_time
    game.best_player_id = best.id if best else None
    game.notes = notes.strip()

    if game.ranked and not game.is_final:  # the game is unranked, so doing elo stuff is silly
        team_one = PlayerGameStats.query.filter(
            (PlayerGameStats.rounds_on_court + PlayerGameStats.rounds_carded > 0) | (game.admin_status == 'Forfeit'),
            PlayerGameStats.team_id == game.team_one_id,
            PlayerGameStats.game_id == game.id).all()
        team_two = PlayerGameStats.query.filter(
            (PlayerGameStats.rounds_on_court + PlayerGameStats.rounds_carded > 0) | (game.admin_status == 'Forfeit'),
            PlayerGameStats.team_id == game.team_two_id,
            PlayerGameStats.game_id == game.id).all()
        teams = [team_one, team_two]
        elos = [0, 0]
        for i, v in enumerate(teams):
            elos[i] = sum(j.player.elo() for j in v)
            elos[i] /= len(v) or 1

        for i in teams:
            my_team = i != teams[0]
            win = game.winning_team_id == i[0].team_id
            for j in i:
                player_id = j.player_id
                elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
                add = EloChange(game_id=game.id, player_id=player_id, tournament_id=game.tournament_id,
                                elo_delta=elo_delta)
                db.session.add(add)
    games_left_in_round = Games.query.filter(Games.tournament_id == game.tournament_id, Games.is_bye == False,
                                             Games.ended == False).all()
    tournament = game.tournament
    sync(game_id)
    logger.info(games_left_in_round)
    if not games_left_in_round:
        if not tournament.in_finals:
            fixtures = get_type_from_name(tournament.fixtures_type, tournament.id)
            fixtures.end_of_round()
        if tournament.in_finals and not tournament.finished:
            finals = get_type_from_name(tournament.finals_type, tournament.id)
            finals.end_of_round()
    db.session.commit()


def substitute(game_id, first_team, left_player):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "Substitute", first_team, left_player)
    db.session.commit()


def create_game(tournament_id, team_one, team_two, official=None, players_one=None, players_two=None, round_number=-1,
                court=0, is_final=False):
    """Pass team_one & team_two in as either int (team id) or str (searchable_name)."""
    if isinstance(tournament_id, str):
        tournament_id = Tournaments.query.filter(Tournaments.searchable_name == tournament_id).first().id
    if players_one is not None:
        players = [-1, -1, -1]
        for i, v in enumerate(players_one):
            player = People.query.filter(People.searchable_name == v).first()
            players[i] = player.id if player else -1
        teams = Teams.query.all()
        first_team = None
        for i in teams[1:]:
            if not i.captain_id:
                continue  # this is most likely the bye team, or it's so fucked up in the db that we probs wanna skip it anyway
            logger.info(players)
            if sorted([i.non_captain_id or -1, i.captain_id, i.substitute_id or -1]) == sorted(players):
                first_team = i
                break
        if not first_team:
            if len([i for i in players if i > 0]) == 1:
                team_one = "(Solo) " + People.query.filter(People.id == players[0]).first().name
            if not team_one:
                raise NameError("You need to give a new team a name!")
            players = [i if i > 0 else None for i in players]
            add = Teams(name=team_one, searchable_name=searchable_of(team_one), captain_id=players[0],
                        non_captain_id=players[1], substitute_id=players[2])
            db.session.add(add)
            first_team = add
    else:
        if isinstance(team_one, int):
            first_team = Teams.query.filter(Teams.id == team_one).first()
        else:
            first_team = Teams.query.filter(Teams.searchable_name == team_one).first()
    if players_two is not None:
        players = [-1, -1, -1]
        for i, v in enumerate(players_two):
            player = People.query.filter(People.searchable_name == v).first()
            players[i] = player.id if player else -1
        teams = Teams.query.all()
        second_team = None
        for i in teams[1:]:
            if not i.captain_id:
                continue  # this is most likely the bye team, or it's so fucked up in the db that we probs wanna skip it anyway
            logger.debug(players)
            if sorted([i.non_captain_id or -1, i.captain_id, i.substitute_id or -1]) == sorted(players):
                second_team = i
                break
        if not second_team:
            if len([i for i in players if i > 0]) == 1:
                team_two = "(Solo) " + People.query.filter(People.id == players[0]).first().name
            if not team_two:
                raise NameError("You need to give a new team a name!")
            players = [i if i > 0 else None for i in players]
            add = Teams(name=team_two, searchable_name=searchable_of(team_two), captain_id=players[0],
                        non_captain_id=players[1], substitute_id=players[2])
            db.session.add(add)
            second_team = add
    else:
        if isinstance(team_two, int):
            second_team = Teams.query.filter(Teams.id == team_two).first()
        else:
            second_team = Teams.query.filter(Teams.searchable_name == team_two).first()
    ranked = True
    for i in [first_team, second_team]:
        if i == 1: continue
        if not TournamentTeams.query.filter(TournamentTeams.team_id == i.id,
                                            TournamentTeams.tournament_id == tournament_id):
            t = TournamentTeams(tournament_id=tournament_id, team_id=i)
            db.session.add(t)
        ranked &= i.non_captain is not None
    if official is not None:
        person = People.query.filter(People.searchable_name == official).first()
        official = Officials.query.filter(Officials.person_id == person.id).first().id

    if round_number < 0:
        last_start = Games.query.filter(Games.tournament_id == tournament_id).order_by(
            Games.start_time.desc()).first()
        if not last_start:
            last_start, round_number = (-1, 0)
        else:
            last_start, round_number = last_start.start_time, last_start.round
        if (
                time.time()
                - last_start
                > 32400
        ):
            round_number = round_number + 1
    is_bye = 1 in [first_team.id, second_team.id]
    court = -1 if is_bye else court
    if is_bye and first_team.id == 1:
        first_team, second_team = second_team, first_team

    g = Games(tournament_id=tournament_id, team_one_id=first_team.id, team_two_id=second_team.id,
              official_id=official, court=court, is_final=is_final, round=round_number, ranked=ranked, is_bye=is_bye,
              someone_has_won=is_bye)
    if is_bye:
        g.noteable_status = "Bye"
        g.admin_status = "Bye"
        g.someone_has_won = True
        g.winning_team_id = 1
    db.session.add(g)
    db.session.commit()  # this is a risk, but i want this to work so ¯\_(ツ)_/¯
    for i, opp in [(first_team, second_team), (second_team, first_team)]:
        players = [i.captain_id, i.non_captain_id, i.substitute_id]
        for j in players:
            if not j: break
            p = PlayerGameStats(game_id=g.id, player_id=j, team_id=i.id, opponent_id=opp.id,
                                tournament_id=tournament_id)
            db.session.add(p)
    db.session.commit()
    return g.id


def create_tournament(name, fixtures_gen, finals_gen, ranked, two_courts, scorer, teams: list[int] = None,
                      officials: list[int] = None):
    officials = officials or []
    teams = teams or []
    searchable_name = searchable_of(name)
    tournament = Tournaments(name=name,
                             searchable_name=searchable_name,
                             fixtures_type=fixtures_gen,
                             finals_type=finals_gen,
                             ranked=ranked,
                             two_courts=two_courts,
                             has_scorer=scorer,
                             image_url='/api/tournaments/image?name=' + searchable_name
                             )

    db.session.add(tournament)
    for i in teams:
        tt = TournamentTeams(tournament_id=tournament.id, team_id=i.id)
        db.session.add(tt)
    for i in officials:
        to = TournamentOfficials(tournament_id=tournament.id, official_id=i.id, is_scorer=True, is_official=True)
        db.session.add(to)
    db.session.commit()
    fixtures = get_type_from_name(fixtures_gen, tournament)
    fixtures.begin_tournament()


def get_timeout_time(game_id):
    """Returns the time which the timeout expires"""
    most_recent_end = (GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'End Timeout')
                       .order_by(GameEvents.id.desc()).first())
    if most_recent_end:
        most_recent_end = most_recent_end.id
    else:
        most_recent_end = -1
    last_time_out = GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'Timeout',
                                            GameEvents.id > most_recent_end).order_by(GameEvents.id.desc()).first()
    if not last_time_out: return 0
    time_out_time = last_time_out.created_at
    return time_out_time + 30 if (time_out_time > 0) else 0

def get_last_score_time(game_id):
    most_recent_score = (GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'Score')
                       .order_by(GameEvents.id.desc()).first())
    
    if not most_recent_score: return -1
    return most_recent_score.created_at + 20 if (most_recent_score.created_at or -1) + 25 > time.time() else -1


def get_timeout_caller(game_id):
    """Returns if the first team listed called the timeout"""
    game = Games.query.filter(Games.id == game_id).first()
    last_time_out = GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'Timeout').order_by(
        GameEvents.id.desc()).first()
    if last_time_out:
        return last_time_out.team_id
    else:
        return False


def delete(game_id):
    if game_is_ended(game_id):
        raise ValueError("Game is Already Over!")
    GameEvents.query.filter(GameEvents.game_id == game_id).delete()
    PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).delete()
    Games.query.filter(Games.id == game_id).delete()
    db.session.commit()


def resolve_game(game_id):
    _add_to_game(game_id, "Resolve", None, None)
    Games.query.filter(Games.id == game_id).first().admin_status = "Resolved"
    db.session.commit()


def serve_timer(game_id, start):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    game = Games.query.filter(Games.id == game_id).first()
    if start:
        game.serve_timer = time.time() + 8
    else:
        game.serve_timer = -1
    db.session.commit()


def get_serve_timer(game_id):
    game = Games.query.filter(Games.id == game_id).first()
    if not game:
        return -1
    return game.serve_timer if (game.serve_timer or -1) + 3 > time.time() else -1


def pardon(game_id, first_team, left_player):
    _add_to_game(game_id, "Pardon", first_team, left_player)
