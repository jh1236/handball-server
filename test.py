import tournaments
from tournaments.Fixtures import Fixtures
from tournaments.Tournament import Tournament

competition: Tournament = Tournament()
print(competition.teams)


def teams():
    return {i.name: [j.name for j in i.players] for i in competition.teams}


def current_games():
    return [i.as_map() for i in competition.fixtures.rounds[-1]]


def all_fixtures():
    return [i.as_map() for i in competition.fixtures.games_to_list()]


def display(game_id):
    return competition.fixtures.get_game(game_id).display_map()


def score(game_id, ace, first_team, first_player):
    competition.fixtures.get_game(game_id).teams[first_team].score_point(first_player, ace)
    competition.fixtures.get_game(game_id).print_gamestate()
    return "", 204


def start(game_id, firstTeamServes, swapTeamOne, swapTeamTwo):
    competition.fixtures.get_game(game_id).start(firstTeamServes, swapTeamOne, swapTeamTwo)
    competition.fixtures.get_game(game_id).print_gamestate()
    return "", 204


def end(game_id, best_player):
    competition.fixtures.get_game(game_id).end(best_player)
    competition.fixtures.get_game(game_id).print_gamestate()
    return "", 204


def timeout(game_id, first_team):
    competition.fixtures.get_game(game_id).teams[first_team].timeout()
    competition.fixtures.get_game(game_id).print_gamestate()
    return "", 204


def undo(game_id):
    competition.fixtures.get_game(game_id).undo()
    competition.fixtures.get_game(game_id).print_gamestate()
    return "", 204


def card(game_id, color, first_team, first_player, time=3):
    if color == "green":
        competition.fixtures.get_game(game_id, ).teams[first_team].green_card(first_player)
    elif color == "yellow":
        competition.fixtures.get_game(game_id).teams[first_team].yellow_card(first_player, time)
    elif color == "red":
        competition.fixtures.get_game(game_id).teams[first_team].red_card(first_player)

    competition.fixtures.get_game(game_id).print_gamestate()
    return "", 204


start(0, False, False, False)
score(0, False, True, True)
score(0, False, True, True)
score(0, False, True, True)
card(0, "red", True, True)
undo(0, )
card(0, "red", True, True)
card(0, "red", True, False)
end(0, "Olivia Stronach")
start(1, False, False, False)
print([[j.fixture_to_table_row() for j in i] for i in competition.fixtures.rounds])

undo(1, )
undo(1, )
undo(1, )
undo(1, )
undo(1, )
undo(1, )
undo(1, )
undo(1, )
score(1, False, True, True)
score(1, False, True, True)
score(1, False, True, True)
card(1, "red", True, True)
card(1, "red", True, False)
start(2, False, False, False)
score(2, False, True, True)
score(2, False, True, True)
score(2, False, True, True)
card(2, "red", True, True)
card(2, "red", True, False)
start(3, False, False, False)
card(3, "red", True, True)
card(3, "red", True, False)
start(4, False, False, False)
card(4, "red", True, True)
card(4, "red", True, False)
start(5, False, False, False)
card(5, "red", True, True)
card(5, "red", True, False)
start(6, False, False, False)
card(6, "red", True, True)
card(6, "red", True, False)
start(7, False, False, False)
card(7, "red", True, True)
card(7, "red", True, False)
for i in competition.fixtures.rounds:
    print([j.fixture_to_table_row() for j in i])
