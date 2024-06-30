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
                for i in players_on_court:
                    if i.card_time_remaining == 0:
                        i.rounds_on_court += 1
                    else:
                        i.rounds_carded += 1
                        if i.card_time_remaining > 0:
                            i.card_time_remaining -= 1
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
    return Games.query.filter(Games.id == game_id).someone_has_won


def game_is_ended(game_id):
    return Games.query.filter(Games.id == game_id).ended


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
        player_on = [i for i in all_players if not i.id in [j.id for j in players] and i.team_id == team.id][0]
        if first_team:
            team_one[not left_player] = player_on
        else:
            team_two[not left_player] = player_on
    if swap:
        last_time_served = GameEvents.query.filter(
            (GameEvents.game_id == game_id) & (GameEvents.team_who_served_id == next_team_to_serve)).order_by(
            GameEvents.id.desc()).first()
        if not last_time_served:
            print("this is my first time serving?!")
            next_serve_side = 'Left'
            next_player_to_serve = team_one[0] if next_team_to_serve == game.team_one_id else team_two[0]
        else:
            next_serve_side = 'Right' if last_time_served.side_served == 'Left' else 'Left'
            new_right = next_serve_side == 'Right'
            next_player_to_serve = team_one[new_right] if next_team_to_serve == game.team_one_id else team_two[
                new_right]
    else:
        next_player_to_serve, next_serve_side = player_who_served, serve_side

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
    if notes != "Penalty":
        if "Card" in char and game.player_to_serve.card_time_reamining != 0:
            if to_add.team_to_serve_id == game.team_one_id:
                to_add.player_to_serve_id = [i.id for i in team_one if i.card_time_remaining == 0][0]
            else:
                to_add.player_to_serve_id = [i.id for i in team_two if i.card_time_remaining == 0][0]
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
    with DatabaseManager() as c:
        if color in ["Green", "Yellow", "Red"]:
            color += " Card"
        _add_to_game(game_id, c, color, first_team, left_player, notes=reason, details=duration)
        team = get_information.get_team_id_from_game_and_side(game_id, first_team, c)
        both_carded = c.execute(
            """SELECT MIN(iif(card_time_remaining < 0, 12, card_time_remaining))
FROM games
         INNER JOIN main.gameEvents gE on gE.id = (SELECT MAX(id) FROM gameEvents WHERE games.id = gE.game_id)
         INNER JOIN playerGameStats ON games.id = playerGameStats.game_id AND (team_one_left_id = playerGameStats.player_id OR
                                                                              team_one_right_id = playerGameStats.player_id OR
                                                                              team_two_left_id = playerGameStats.player_id OR
                                                                              team_two_right_id = playerGameStats.player_id)
WHERE playerGameStats.game_id = ?
  AND playerGameStats.team_id = ?""",
            (game_id, team)).fetchone()[0]
        if both_carded != 0:
            my_score, their_score, someone_has_won = c.execute(
                """SELECT team_one_score, team_two_score, games.someone_has_won FROM games WHERE games.id = ?""",
                (game_id,)).fetchone()
            if someone_has_won:
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
    return GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first().id


def time_out(game_id, first_team):
    _add_to_game(game_id, "Timeout", first_team, None)


def forfeit(game_id, first_team):
    _add_to_game(game_id, "Forfeit", first_team, None)


def end_timeout(game_id):
    _add_to_game(game_id, "End Timeout", None, None)


def end_game(game_id, bestPlayer,
             notes, protest_team_one, protest_team_two):
    with DatabaseManager() as c:
        tournament_id = c.execute("""SELECT tournament_id FROM games WHERE id = ?""", (game_id,)).fetchone()[0]
        best = c.execute("""SELECT id FROM people WHERE searchable_name = ?""", (bestPlayer,)).fetchone()
        if best:
            best = best[0]
        else:
            allowed = c.execute("""SELECT SUM(event_type = 'Forfeit') > 0 FROM gameEvents WHERE game_id = ?""",
                                (game_id,)).fetchone()[0]
            allowed |= bool(c.execute("""SELECT teams.id FROM games INNER JOIN teams ON 
            (teams.id = games.team_one_id or games.team_two_id = teams.id) WHERE (teams.non_captain_id is null) AND games.id = ?""",
                                      (game_id,)).fetchone())
            if not allowed:
                raise ValueError("Best Player was not provided")
        if protest_team_one:
            _add_to_game(game_id, c, "Protest", True, None, notes=protest_team_one)
        if protest_team_two:
            _add_to_game(game_id, c, "Protest", False, None, notes=protest_team_two)
        _add_to_game(game_id, c, "End Game", None, None, notes=notes, details=best)
        teams = c.execute("""
SELECT games.ranked and not games.is_final as ranked,
       games.winning_team_id = team_id as myTeamWon,
       games.team_one_id <> playerGameStats.team_id as isSecond,
       ROUND(1500.0 + coalesce((SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = playerGameStats.player_id), 0), 2) as elo,
       player_id as player
       FROM playerGameStats
         INNER JOIN games ON playerGameStats.game_id = games.id
WHERE games.id = ? ORDER BY isSecond""", (game_id,)).fetchall()

        protested, red_cards, yellow_cards, start_time = c.execute("""SELECT protested,
       SUM(playerGameStats.red_cards) > 0,
       SUM(playerGameStats.yellow_cards) > 0,
       start_time
FROM games
         INNER JOIN main.playerGameStats on playerGameStats.game_id = games.id
         WHERE games.id = ?""", (game_id,)).fetchone()

        if red_cards:
            c.execute("""UPDATE games SET admin_status = 'Red Card Awarded' WHERE id = ?""", (game_id,))
        elif protested:
            c.execute("""UPDATE games SET admin_status = 'Protested' WHERE id = ?""", (game_id,))
        elif notes.strip():
            c.execute("""UPDATE games SET admin_status = 'Notes To Review' WHERE id = ?""", (game_id,))
        elif yellow_cards:
            c.execute("""UPDATE games SET admin_status = 'Yellow Card Awarded' WHERE id = ?""", (game_id,))
        else:
            c.execute("""UPDATE games SET admin_status = 'Official' WHERE id = ?""", (game_id,))
        end_time = time.time() - start_time

        c.execute(
            """UPDATE games SET status = 'Official', main.games.noteable_status = admin_status, length = ?, best_player_id = ?, notes = ? WHERE id = ?""",
            (end_time, best, notes.strip(), game_id,))

        if teams[0][0]:  # the game is unranked, so doing elo stuff is silly
            elos = [0, 0]
            team_sizes = [0, 0]
            for i in teams:
                elos[i[2]] += i[3]
                team_sizes[i[2]] += 1
            for i, v in enumerate(team_sizes):
                elos[i] /= v
            print(elos)
            for i in teams:
                win = i[1]
                my_team = i[2]
                player_id = i[4]
                elo_delta = calc_elo(elos[my_team], elos[not my_team], win)
                c.execute("""INSERT INTO eloChange(game_id, player_id, tournament_id, elo_delta) VALUES (?, ?, ?, ?)""",
                          (game_id, player_id, tournament_id, elo_delta))
        end_of_round = c.execute(
            """SELECT id FROM games WHERE not games.is_bye AND games.tournament_id = ? AND not games.ended""",
            (tournament_id,)).fetchone()
        fixture_gen, finals_gen, in_finals, finished = c.execute(
            """SELECT fixtures_type, finals_type, in_finals, finished FROM tournaments WHERE tournaments.id = ?""",
            (tournament_id,)).fetchone()

        sync(c, game_id)

    if not end_of_round:
        if not in_finals:
            fixtures = get_type_from_name(fixture_gen, tournament_id)
            fixtures.end_of_round()
            with DatabaseManager() as c:
                in_finals = c.execute("""SELECT in_finals FROM tournaments WHERE tournaments.id = ?""",
                                      (tournament_id,)).fetchone()[0]
        if in_finals and not finished:
            print(in_finals)
            print(finished)
            finals = get_type_from_name(finals_gen, tournament_id)
            finals.end_of_round()


def substitute(game_id, first_team, left_player):
    _add_to_game(game_id, "Substitute", first_team, left_player)


def create_game(tournament_id, team_one, team_two, official=None, players_one=None, players_two=None, round_number=-1,
                court=0, is_final=False):
    """Pass team_one & team_two in as either int (team id) or str (searchable_name)."""
    with DatabaseManager() as c:
        if isinstance(tournament_id, str):
            tournament_id = \
                c.execute("""SELECT id FROM tournaments WHERE tournaments.searchable_name = ?""",
                          (tournament_id,)).fetchone()[0]
        if players_one is not None:
            players = [None, None, None]
            for i, v in enumerate(players_one):
                players[i] = c.execute("""SELECT id FROM people WHERE people.searchable_name = ?""", (v,)).fetchone()[0]
            print(players)
            first_team = c.execute("""SELECT id
FROM teams
WHERE (captain_id = ? or non_captain_id = ? or substitute_id = ?)
  AND IIF(? is null, 1, (captain_id = ? or non_captain_id = ? or substitute_id = ?))
  AND IIF(? is null, 1, (captain_id = ? or non_captain_id = ? or substitute_id = ?))
""",
                                   (players[0], players[0], players[0], players[1], players[1], players[1], players[1],
                                    players[2],
                                    players[2], players[2], players[2])).fetchone()
            if first_team:
                first_team = first_team[0]
            else:
                c.execute(
                    """INSERT INTO teams(name, searchable_name, captain_id, non_captain_id, substitute_id) VALUES (?, ?, ?, ?, ?)""",
                    (team_one, searchable_of(team_one), players[0], players[1], players[2]))
                first_team = c.execute("""SELECT id FROM teams ORDER BY id DESC LIMIT 1""").fetchone()[0]
        else:
            if isinstance(team_one, int):
                first_team = team_one
            else:
                first_team = c.execute("""SELECT id FROM teams WHERE searchable_name = ?""", (team_one,)).fetchone()[0]
        if players_two is not None:
            players = [None, None, None]
            for i, v in enumerate(players_two):
                players[i] = c.execute("""SELECT id FROM people WHERE people.searchable_name = ?""", (v,)).fetchone()[0]

            second_team = c.execute("""SELECT id
FROM teams
WHERE (captain_id = ? or non_captain_id = ? or substitute_id = ?)
  AND IIF(? is null, 1, (captain_id = ? or non_captain_id = ? or substitute_id = ?))
  AND IIF(? is null, 1, (captain_id = ? or non_captain_id = ? or substitute_id = ?))
""",
                                    (players[0], players[0], players[0], players[1], players[1], players[1], players[1],
                                     players[2],
                                     players[2], players[2], players[2])).fetchone()
            if second_team:
                second_team = second_team[0]
            else:
                c.execute(
                    """INSERT INTO teams(name, searchable_name, captain_id, non_captain_id, substitute_id) VALUES (?, ?, ?, ?, ?)""",
                    (team_two, searchable_of(team_two), players[0], players[1], players[2]))
                second_team = c.execute("""SELECT id FROM teams ORDER BY id DESC LIMIT 1""").fetchone()[0]
        else:
            if isinstance(team_two, int):
                second_team = team_two
            else:
                second_team = c.execute("""SELECT id FROM teams WHERE searchable_name = ?""", (team_two,)).fetchone()[0]

        ranked = True

        for i in [first_team, second_team]:
            if i == 1: continue
            if c.execute("""SELECT id FROM tournamentTeams WHERE team_id = ? AND tournament_id = ?""",
                         (i, tournament_id)).fetchone() is None:
                c.execute(
                    """INSERT INTO tournamentTeams(tournament_id, team_id) VALUES (?, ?)""",
                    (
                        tournament_id, i
                    ))
            ranked &= c.execute(
                """SELECT teams.non_captain_id FROM teams WHERE teams.id = ?""",
                (i,)).fetchone()[0] != None
        if official is not None:
            official = c.execute(
                """SELECT officials.id FROM officials INNER JOIN people ON person_id = people.id WHERE searchable_name = ?""",
                (official,)).fetchone()[0]

        if round_number < 0:
            last_start = c.execute(
                """SELECT start_time, round FROM games WHERE tournament_id = ? ORDER BY id DESC LIMIT 1""",
                (tournament_id,)).fetchone()
            if not last_start:
                last_start, round_number = (-1, 0)
            else:
                last_start, round_number = last_start
            last_start = last_start or 1
            if (
                    time.time()
                    - last_start
                    > 32400 and
                    round_number < 0
            ):
                round_number = round_number + 1
        is_bye = 1 in [first_team, second_team]
        court = -1 if is_bye else court
        if is_bye and first_team == 1:
            first_team, second_team = second_team, first_team

        c.execute("""
            INSERT INTO games(tournament_id, team_one_id, team_two_id, official_id, iga_side_id,  court, is_final, round, is_bye, status, ranked, team_one_score, team_two_score, team_one_timeouts, team_two_timeouts, started, ended) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Waiting For Start', ?, 0, 0, 0, 0, ?, ?)
        """, (
            tournament_id, first_team, second_team, official, first_team, court, is_final, round_number, is_bye, ranked,
            is_bye, is_bye))
        game_id = c.execute("""SELECT id from games order by id desc limit 1""").fetchone()[0]
        for i, opp in [(first_team, second_team), (second_team, first_team)]:
            players = c.execute(
                """SELECT people.id FROM people INNER JOIN teams ON people.id = teams.captain_id or people.id = teams.non_captain_id or people.id = teams.substitute_id WHERE teams.id = ?""",
                (i,)).fetchall()
            for j in players:
                c.execute(
                    """INSERT INTO playerGameStats(game_id, player_id, team_id, opponent_id, tournament_id, rounds_on_court, rounds_carded) VALUES (?, ?, ?, ?, ?, 0, 0)""",
                    (game_id, j[0], i, opp, tournament_id))
        return game_id


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
    with DatabaseManager() as c:
        time_out_time = (c.execute("""SELECT created_at
                    FROM gameEvents
                    WHERE game_id = ?
                      AND event_type = 'Timeout'
                      AND not EXISTS(SELECT id
                                     FROM gameEvents i
                                     WHERE i.id > gameEvents.id
                                     AND i.game_id = gameEvents.game_id
                                       AND i.event_type = 'End Timeout')""", (game_id,)).fetchone() or [-1])[0]
        return time_out_time + 30 if (time_out_time > 0) else 0


def get_timeout_caller(game_id):
    """Returns if the first team listed called the timeout"""
    with DatabaseManager() as c:
        time_out_time = (c.execute("""SELECT team_id == games.team_one_id
                    FROM gameEvents INNER join games on gameEvents.game_id = games.id
                    WHERE games.Id = ?
                      AND event_type = 'Timeout'
                      AND not EXISTS(SELECT i.id
                                     FROM gameEvents i
                                     WHERE i.id > gameEvents.id
                                     AND i.game_id = gameEvents.game_id
                                       AND i.event_type = 'End Timeout') ORDER BY gameEvents.id desc LIMIT 1""",
                                   (game_id,)).fetchone() or [0])[0]
        return time_out_time


def delete(game_id):
    with DatabaseManager() as c:
        c.execute("""DELETE FROM playerGameStats WHERE playerGameStats.game_id = ?""", (game_id,))
        c.execute("""DELETE FROM gameEvents WHERE gameEvents.game_id = ?""", (game_id,))
        c.execute("""DELETE FROM games WHERE games.id = ?""", (game_id,))


def resolve_game(game_id):
    _add_to_game(game_id, "Resolve", None, None)
    Games.query.filter(Games.id == game_id).first().admin_status = "Resolved"
