import logging
import threading
from random import Random

from start import comps, app
from utils.logging_handler import logger

competition = comps["fifth_suss_championship"]

logger.debug(competition.teams)


def teams():
    return {i.name: [j.name for j in i.players] for i in competition.teams}


def current_games():
    return [i.as_map() for i in competition.fixtures[-1]]


def all_fixtures():
    return [i.as_map() for i in competition.games_to_list()]


def display(game_id):
    return competition.get_game(game_id).display_map()


def score(game_id, ace, first_team, first_player):
    competition.get_game(game_id).teams[not first_team].score_point(first_player, ace)
    competition.save()


def start(game_id, first_team_served, swap_team_one, swap_team_two):
    competition.get_game(game_id).start(first_team_served, swap_team_one, swap_team_two)
    competition.save()


def end(game_id, best_player):
    competition.get_game(game_id).end()
    competition.save()


def timeout(game_id, first_team):
    competition.get_game(game_id).teams[not first_team].timeout()
    competition.save()


def endTimeout(game_id, first_team):
    competition.get_game(game_id).teams[not first_team].end_timeout()
    competition.save()


def undo(game_id):
    competition.get_game(game_id).undo()
    competition.save()


def card(game_id, color, first_team, first_player, time=3):
    if color == "green":
        competition.get_game(game_id).teams[not first_team].green_card(first_player)
    elif color == "yellow":
        competition.get_game(game_id).teams[not first_team].yellow_card(
            first_player, time
        )
    elif color == "red":
        competition.get_game(game_id).teams[not first_team].red_card(first_player)
    else:
        raise Exception(f"Illegal argument {color}")
    competition.save()


def fault(game_id, first_team):
    competition.get_game(game_id).teams[not first_team].fault()
    competition.get_game(game_id).print_gamestate()
    competition.save()


if __name__ == "__main__":
    threading.Thread(target = lambda: app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)).start()
    random = Random()
    logger.setLevel(logging.CRITICAL)

    def r_bool():
        return bool(random.randint(0, 1))

    once = False
    winners = True
    while not once or (
        "Bedwars" not in competition.get_game(-1).winner().name and winners
    ):
        once = True
        print(
            f"Winner was {competition.get_game(-1).winner().name}, rejecting"
        )
        competition.dump()
        game_id = 0
        game_count = 40
        competition.get_game(game_id).start(r_bool(), r_bool(), r_bool())
        while True:
            try:
                game = competition.get_game(game_id)
                if game.bye:
                    game_id += 1
                    competition.get_game(game_id).start(r_bool(), r_bool(), r_bool())
                    continue
                if competition.get_game(game_id).game_ended():
                    game.end(game.players()[0].name)
                    game_id += 1
                    while competition.get_game(game_id).bye:  # the game is a bye
                        game_id += 1
                    competition.get_game(game_id).start(r_bool(), r_bool(), r_bool())
                    continue
                competition.update_games()
                code = random.randint(0, 20)
                if code <= 10:
                    ace = r_bool()
                    score(game_id, r_bool(), None if ace else r_bool(), ace)
                elif code <= 15:
                    fault(game_id, r_bool())
                elif code == 17:
                    t = r_bool()
                    timeout(game_id, t)
                    endTimeout(game_id, t)
                else:
                    choice = random.choice(["green", "yellow"])
                    card(game_id, choice, r_bool(), r_bool())
            except ValueError:
                print("Error")
                break
    print("-" * 20)
    for i, t in enumerate(sorted(competition.teams, key=lambda a: -a.games_won)):
        print(f"{i + 1}: {t.name} [{t.first_ratio()}] [{t.court_one}]")
    print("-" * 20)
    for t in competition.officials:
        print(f": {t.name} [{t.internal_games_umpired}] [{t.games_court_one /(t.internal_games_umpired or 1)}] <{t.internal_games_scored}>")
    print("-" * 20)

