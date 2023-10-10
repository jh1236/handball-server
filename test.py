from random import Random

from api import comps, app
from utils.logging_handler import logger

competition = comps["second_suss_championship"]

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
    return "", 204


def start(game_id, first_team_served, swap_team_one, swap_team_two):
    competition.get_game(game_id).start(first_team_served, swap_team_one, swap_team_two)
    competition.save()
    return "", 204


def end(game_id, best_player):
    competition.get_game(game_id).end()
    competition.save()
    return "", 204


def timeout(game_id, first_team):
    competition.get_game(game_id).teams[not first_team].timeout()
    competition.save()
    return "", 204


def undo(game_id):
    competition.get_game(game_id).undo()
    competition.save()
    return "", 204


def card(game_id, color, first_team, first_player, time=3):
    if color == "green":
        competition.get_game(game_id).teams[not first_team].green_card(first_player)
    elif color == "yellow":
        competition.get_game(game_id).teams[not first_team].yellow_card(first_player, time)
    elif color == "red":
        competition.get_game(game_id).teams[not first_team].red_card(first_player)
    else:
        raise Exception(f"Illegal argument {color}")
    competition.save()
    return "", 204


def fault(game_id, first_team):
    competition.get_game(game_id).teams[not first_team].fault()
    competition.get_game(game_id).print_gamestate()
    competition.save()
    return "", 204


if __name__ == "__main__":
    random = Random()


    def r_bool():
        return bool(random.randint(0, 1))


    once = False
    winners = True
    while not once or ("Official" not in competition.get_game(-1).winner().name and winners):
        once = True
        print(f"Winner was {sorted(competition.teams, key=lambda a: -a.games_won)[0].name}, rejecting")
        competition.dump()
        game_id = 0
        game_count = 40
        competition.get_game(game_id).start(r_bool(), r_bool(), r_bool())
        while True:
            try:
                game = competition.get_game(game_id)
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
                    timeout(game_id, r_bool())
                else:
                    choice = random.choice(["green", "yellow"] * 2 + ["red"])
                    card(game_id, choice, r_bool(), r_bool())
            except ValueError:
                print("Error")
                break
    print("-" * 20)
    for i, t in enumerate(sorted(competition.teams, key=lambda a: -a.games_won)):
        print(f"{i + 1}: {t.name} [{t.first_ratio()}] [{t.court_one}]")
    print("-" * 20)
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
