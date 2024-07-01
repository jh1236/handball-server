import re
import time

from FixtureGenerators.FixturesGenerator import get_type_from_name
from database import db
from database.database_utilities import on_court_for_game
from database.models import *
from structure import get_information
from utils.databaseManager import DatabaseManager
from utils.statistics import calc_elo

SIDES = ["Left", "Right", "Substitute"]


def searchable_of(name: str):
    s = name.lower().replace(" ", "_").replace(",", "").replace("the_", "")
    return re.sub("[^a-zA-Z0-9_]", "", s)


def sync(game_id):
    game: Games = Games.query.filter(Games.id == game_id).first()
    game.reset()
    events: list[GameEvents] = GameEvents.query.filter_by(game_id=game_id).order_by(GameEvents.id).all()
    all_players: list[PlayerGameStats] = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
    fault = False

    for i in all_players:
        i.reset_stats()
        old_card_time = PlayerGameStats.query.filter((PlayerGameStats.player_id == i.player_id) &
                                                     (PlayerGameStats.tournament_id == i.tournament_id) &
                                                     (PlayerGameStats.game_id < i.game_id)).order_by(
            PlayerGameStats.game_id.desc()).first()
        if old_card_time:
            old_card_time = old_card_time.card_time_remaining
        else:
            old_card_time = 0
        i.card_time_remaining = max(old_card_time, 0)
        i.card_time = i.card_time_remaining
    i = None
    for i in events:
        players_on_court = on_court_for_game(game_id, None)
        is_team_one = i.team_id == game.team_one_id
        player: PlayerGameStats = ([j for j in all_players if j.player_id == i.player_id] + [None])[0]
        match i.event_type:
            case "Score":
                fault = False
                if i.details != "Penalty":
                    player.points_scored += 1
                    player_who_served = [j for j in all_players if j.player_id == i.player_who_served_id][0]
                    player_who_served.served_points += 1
                    if player_who_served.team_id == i.team_id:
                        player_who_served.served_points += 1
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
            case "Ace":
                player.aces_scored += 1
            case "Fault":
                player.faults += 1
                if fault:
                    player.double_faults += 1
                    fault = False
                else:
                    fault = True
            case "Green Card":
                player.green_cards += 1
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
                game.notes = i.notes
                game.winning_team_id = game.team_one if game.team_one_score > game.team_two_score else game.team_two
            case "Start":
                game.started = True
            case _:
                pass
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


def _add_to_game(game_id, char: str, first_team, left_player, team_to_serve=None, details=None, notes=None):
    """IMPORTANT: if the item added to game is a penalty, THE CALLER IS RESPONSIBLE FOR SYNCING"""
    game = Games.query.filter(Games.id == game_id).first()
    team = Teams.query.filter(Teams.id == (game.team_one_id if first_team else game.team_two_id)).first()
    last_game_event = GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first()
    player: PlayerGameStats
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
    swap = team_who_served != next_team_to_serve
    team_one = [last_game_event.team_one_left, last_game_event.team_one_right]
    team_two = [last_game_event.team_two_left, last_game_event.team_two_right]
    if char == "Substitute":
        all_players = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
        player_on = [i for i in all_players if i.id not in [j.id for j in players] and i.team_id == team.id][0]
        if first_team:
            team_one[not left_player] = player_on.player
        else:
            team_two[not left_player] = player_on.player
    if swap:
        last_time_served = GameEvents.query.filter(
            (GameEvents.game_id == game_id) & (GameEvents.team_who_served_id == next_team_to_serve)).order_by(
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
        serve_team = team_one if next_team_to_serve == game.team_one_id else team_two
        next_player_to_serve = serve_team[next_serve_side == 'Right']

    print(serve_side)

    to_add = GameEvents(game_id=game.id, tournament_id=game.tournament_id, event_type=char,
                        details=details, notes=notes, team_id=team.id, player_id=player.id,
                        team_who_served_id=team_who_served, player_who_served_id=player_who_served.id,
                        side_served=serve_side,
                        team_to_serve_id=next_team_to_serve, player_to_serve_id=next_player_to_serve.id,
                        side_to_serve=next_serve_side,
                        team_one_left_id=team_one[0].id,
                        team_one_right_id=team_one[1].id,
                        team_two_left_id=team_two[0].id,
                        team_two_right_id=team_two[1].id)
    db.session.add(to_add)

    sync(game_id)
    server = PlayerGameStats.query.filter(PlayerGameStats.player_id == game.player_to_serve_id,
                                          PlayerGameStats.game_id == game.id).first()
    server_team_players_on_court = [i.player_id for i in players if
                                    i.team_id == to_add.team_to_serve_id and i.card_time_remaining == 0]
    if "Card" in char and server.card_time_remaining != 0 and server_team_players_on_court:
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
    get_information.game_and_side[game_id] = (team_one_id, team_two_id)

    team_one += [None]
    team_two += [None]
    iga = team_one_id if team_one_iga else team_two_id
    game.status = 'In Progress'
    game.admin_status = 'In Progress'
    game.noteable_status = 'In Progress'
    game.iga_side = iga
    game.start_time = time.time()
    if official:
        game.official_id = Officials.query.filter(Officials.person.searchable_name == official).first().id
    if scorer:
        game.official_id = Officials.query.filter(Officials.person.searchable_name == scorer).first().id
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
    db.session.commit()


def score_point(game_id, first_team, left_player):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _score_point(game_id, first_team, left_player)


def ace(game_id):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    game = Games.query.filter(game_id == Games.id).first()
    first_team = bool(game.team_one == game.team_to_serve)
    left_player = bool(game.side_to_serve == 'Left')
    _add_to_game(game_id, "Ace", first_team, left_player)
    _score_point(game_id, first_team, left_player, penalty=True)


def fault(game_id):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    game = Games.query.filter(game_id == Games.id).first()
    first_team = bool(game.team_one == game.team_to_serve)
    left_player = bool(game.side_to_serve == 'Left')
    prev_event = GameEvents.query.filter(GameEvents.game_id == game_id, (GameEvents.event_type == 'Fault') | (
            GameEvents.event_type == 'Score')).first().event_type
    _add_to_game(game_id, "Fault", first_team, left_player)
    if prev_event == "Fault":
        _score_point(game_id, not first_team, None, penalty=True)


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


def undo(game_id):
    delete_after = GameEvents.query.filter(GameEvents.game_id == game_id,
                                           (GameEvents.notes == None) | (GameEvents.notes != 'Penalty'),
                                           GameEvents.event_type != 'Protest').order_by(GameEvents.id.desc()).first().id
    GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.id >= delete_after).delete()
    sync(game_id)
    db.session.commit()


def change_code(game_id):
    return (GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first().id +
            (get_serve_timer(game_id) > 0))


def time_out(game_id, first_team):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "Timeout", first_team, None)


def forfeit(game_id, first_team):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "Forfeit", first_team, None)


def end_timeout(game_id):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "End Timeout", None, None)


def end_game(game_id, best_player, notes, protest_team_one, protest_team_two):
    if not game_is_over(game_id):
        raise ValueError("Game is not yet Over!")
    game = Games.query.filter(Games.id == game_id).first()
    best = People.query.filter(People.searchable_name == best_player).first()
    players = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
    if best is None:
        forfeit = GameEvents.query.filter(GameEvents.event_type == 'Forfeit', GameEvents.game_id == game_id).first()
        teams = [game.team_one, game.team_two]
        if forfeit is None and not [i for i in teams if i.non_captain]:
            raise ValueError("Best Player was not provided")

    if protest_team_one:
        _add_to_game(game_id, "Protest", True, None, notes=protest_team_one)
    if protest_team_two:
        _add_to_game(game_id, "Protest", False, None, notes=protest_team_two)
        _add_to_game(game_id, "End Game", None, None, notes=notes, details=best)

    if any(i.yellow_cards for i in players):
        game.admin_status = 'Red Card Awarded'
    elif protest_team_one or protest_team_two:
        game.admin_status = 'Protested'
    elif notes.strip():
        game.admin_status = 'Notes to Review'
    elif any(i.yellow_cards for i in players):
        game.admin_status = 'Yellow Card Awarded'
    else:
        game.admin_status = 'Official'
    game.noteable_status = game.admin_status

    game.status = 'Official'
    game.length = time.time() - game.start_time
    game.best_player_id = best.id
    game.notes = notes.strip()

    if game.ranked and not game.is_final:  # the game is unranked, so doing elo stuff is silly
        team_one = PlayerGameStats.query.filter((PlayerGameStats.rounds_on_court + PlayerGameStats.rounds_carded) > 0,
                                                PlayerGameStats.team_id == game.team_one_id,
                                                PlayerGameStats.game_id == game.id).all()
        team_two = PlayerGameStats.query.filter((PlayerGameStats.rounds_on_court + PlayerGameStats.rounds_carded) > 0,
                                                PlayerGameStats.team_id == game.team_one_id,
                                                PlayerGameStats.game_id == game.id).all()
        teams = [team_one, team_two]
        elos = [0, 0]
        for i, v in enumerate(teams):
            elos[i] = sum(j.elo() for j in v)
            elos[i] /= len(v)

        print(elos)
        for i in teams:
            my_team = i[0].team_id
            win = game.winning_team_id == my_team
            for j in i:
                player_id = j.player_id
                elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
                add = EloChange(game_id=game.id, player_id=player_id, tournament_id=game.tournament_id,
                                elo_delta=elo_delta)
                db.session.add(add)
    end_of_round = Games.query.filter(Games.tournament_id == game.tournament_id, not Games.is_bye, not Games.is_final)
    tournament = game.tournament
    sync(game_id)

    if not end_of_round:
        if not tournament.in_finals:
            fixtures = get_type_from_name(tournament.fixtures_type, tournament.id)
            fixtures.end_of_round()
        if tournament.in_finals and not tournament.finished:
            finals = get_type_from_name(tournament.finals_type, tournament.id)
            finals.end_of_round()


def substitute(game_id, first_team, left_player):
    if game_is_over(game_id):
        raise ValueError("Game is Already Over!")
    _add_to_game(game_id, "Substitute", first_team, left_player)


def create_game(tournament_id, team_one, team_two, official=None, players_one=None, players_two=None, round_number=-1,
                court=0, is_final=False):
    """Pass team_one & team_two in as either int (team id) or str (searchable_name)."""
    with DatabaseManager() as c:
        if isinstance(tournament_id, str):
            tournament_id = Tournaments.query.filter(Tournaments.searchable_name == tournament_id).first().id
        if players_one is not None:
            players = [None, None, None]
            for i, v in enumerate(players_one):
                players[i] = People.query.filter(People.searchable_name == v).first()
            print(players)
            teams = Teams.query.all()
            first_team = None
            for i in teams:
                if sorted([i.non_captain_id, i.captain_id, i.substitute_id]) == sorted(players):
                    first_team = i
                    break
            if not first_team:
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
            players = [None, None, None]
            for i, v in enumerate(players_two):
                players[i] = People.query.filter(People.searchable_name == v).first()
            print(players)
            teams = Teams.query.all()
            second_team = None
            for i in teams:
                if sorted([i.non_captain_id, i.captain_id, i.substitute_id]) == sorted(players):
                    second_team = i
                    break
            if not second_team:
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
            official = c.execute(
                """SELECT officials.id FROM officials INNER JOIN people ON person_id = people.id WHERE searchable_name = ?""",
                (official,)).fetchone()[0]

        if round_number < 0:
            last_start = Games.query.filter(Games.tournament_id == tournament_id).order_by(
                Games.start_time.desc()).first()
            if not last_start:
                last_start, round_number = (-1, 0)
            else:
                last_start, round_number = last_start.start_time, last_start.round
            last_start = last_start or 1
            if (
                    time.time()
                    - last_start
                    > 32400 and
                    round_number < 0
            ):
                round_number = round_number + 1
        is_bye = 1 in [first_team.id, second_team.id]
        court = -1 if is_bye else court
        if is_bye and first_team.id == 1:
            first_team, second_team = second_team, first_team

        g = Games(tournament_id=tournament_id, team_one_id=first_team.id, team_two_id=second_team.id,
                  official_id=official, court=court, is_final=is_final, round=round_number, ranked=ranked)
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
    with DatabaseManager() as c:
        searchable_name = searchable_of(name)
        c.execute("""INSERT INTO tournaments(name, searchable_name, fixtures_type, finals_type, ranked, two_courts,  has_scorer, image_url, finished, is_pooled, notes, in_finals) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, '', 0)""", (
            name, searchable_name, fixtures_gen, finals_gen, ranked, two_courts, scorer,
            '/api/tournaments/image?name=' + searchable_name))
        tournament = c.execute("""SELECT id FROM tournaments ORDER BY id desc LIMIT 1""").fetchone()[0]
        for i in teams:
            c.execute(
                """INSERT INTO tournamentTeams(tournament_id, team_id, pool) VALUES (?, ?, 0)""",
                (tournament, i))
        for i in officials:
            c.execute(
                """INSERT INTO tournamentOfficials(tournament_id, official_id, is_scorer, is_umpire) VALUES (?, ?, 1, 1)""",
                (tournament, i))
    fixtures = get_type_from_name(fixtures_gen, tournament)
    fixtures.begin_tournament()


def get_timeout_time(game_id):
    """Returns the time which the timeout expires"""
    most_recent_end = GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'End Timeout').id
    last_time_out = GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'Timeout',
                                            GameEvents.id < most_recent_end).first()
    time_out_time = last_time_out.created_at
    return time_out_time + 30 if (time_out_time > 0) else 0


def get_timeout_caller(game_id):
    """Returns if the first team listed called the timeout"""
    game = Games.query.filter(Games.id == game_id).first()
    most_recent_end = GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'End Timeout').id
    last_time_out = GameEvents.query.filter(GameEvents.game_id == game_id, GameEvents.event_type == 'Timeout',
                                            GameEvents.id < most_recent_end).first()
    return last_time_out.team_id == game.team_one_id


def delete(game_id):
    GameEvents.query.filter(GameEvents.game_id == game_id).all().delete()
    PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all().delete()
    Games.query.filter(Games.id == game_id).all().delete()


def resolve_game(game_id):
    _add_to_game(game_id, "Resolve", None, None)
    Games.query.filter(Games.id == game_id).first().admin_status = "Resolved"


def serve_timer(game_id, start):
    game = Games.query.filter(Games.id == game_id).first()
    if start:
        game.serve_timer = time.time() + 8
    else:
        game.serve_timer = -1
    db.session.commit()


def get_serve_timer(game_id):
    game = Games.query.filter(Games.id == game_id).first()
    return game.serve_timer if game.serve_timer + 3 > time.time() else -1
