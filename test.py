from random import Random

from api import competition, app
from utils.logging_handler import logger

competition.load()
print(competition.teams)

logger.debug(competition.teams)


def teams():
    return {i.name: [j.name for j in i.players] for i in competition.teams}


def current_games():
    return [i.as_map() for i in competition.fixtures.fixtures[-1]]


def all_fixtures():
    return [i.as_map() for i in competition.fixtures.games_to_list()]


def display(game_id):
    return competition.fixtures.get_game(game_id).display_map()


def score(game_id, ace, first_team, first_player):
    competition.fixtures.get_game(game_id).teams[not first_team].score_point(first_player, ace)
    competition.fixtures.save()
    return "", 204


def start(game_id, first_team_served, swap_team_one, swap_team_two):
    competition.fixtures.get_game(game_id).start(first_team_served, swap_team_one, swap_team_two)
    competition.fixtures.save()
    return "", 204


def end(game_id, best_player):
    competition.fixtures.get_game(game_id).end()
    competition.fixtures.save()
    return "", 204


def timeout(game_id, first_team):
    competition.fixtures.get_game(game_id).teams[not first_team].timeout()
    competition.fixtures.save()
    return "", 204


def undo(game_id):
    competition.fixtures.get_game(game_id).undo()
    competition.fixtures.save()
    return "", 204


def card(game_id, color, first_team, first_player, time=3):
    if color == "green":
        competition.fixtures.get_game(game_id).teams[not first_team].green_card(first_player)
    elif color == "yellow":
        competition.fixtures.get_game(game_id).teams[not first_team].yellow_card(first_player, time)
    elif color == "red":
        competition.fixtures.get_game(game_id).teams[not first_team].red_card(first_player)
    else:
        raise Exception(f"Illegal argument {color}")
    competition.fixtures.save()
    return "", 204


def fault(game_id, first_team):
    competition.fixtures.get_game(game_id).teams[not first_team].fault()
    competition.fixtures.get_game(game_id).print_gamestate()
    competition.fixtures.save()
    return "", 204


random = Random()


def r_bool():
    return bool(random.randint(0, 1))

print(competition.fixtures.get_game(-1).winner().name)
once = False
while not once or "Official" not in competition.fixtures.get_game(-1).winner().name:
    once = True
    print(f"Winner was {sorted(competition.teams, key=lambda a: -a.games_won)[0].name}, rejecting")
    competition.dump()
    game_id = 0
    game_count = 40
    competition.fixtures.get_game(game_id).start(r_bool(), r_bool(), r_bool())
    while True:
        try:
            game = competition.fixtures.get_game(game_id)
            if competition.fixtures.get_game(game_id).game_ended():
                game.end(game.players()[0].name)
                game_id += 1
                competition.fixtures.get_game(game_id).start(r_bool(), r_bool(), r_bool())
                continue
            competition.fixtures.update_games()
            code = random.randint(0, 11)
            if code <= 7:
                score(game_id, r_bool(), r_bool(), r_bool())
            elif code <= 9:
                choice = random.choice(["green", "yellow"] * 2 + ["red"])
                card(game_id, choice, r_bool(), r_bool())
            elif code == 10:
                timeout(game_id, r_bool())
            elif code == 11:
                fault(game_id, r_bool())
        except ValueError:
            print("Error")
            break
print("-" * 20)
for i, t in enumerate(sorted(competition.teams, key=lambda a: -a.games_won)):
    print(f"{i + 1}: {t.name} [{t.first_ratio()}]")
print("-" * 20)
app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
