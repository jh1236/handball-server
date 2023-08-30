import tournaments
from tournaments.Tournament import Tournament

competition: Tournament = tournaments.Swiss.load()
print(competition.teams)


def teams():
    return {i.name: i.as_map() for i in competition.teams}


def current_games():
    return [i.to_map() for i in competition.rounds[-1] if not i.game.is_over()]


def fixtures():
    return [i.game.as_map() for i in competition.fixtures]


def games():
    competition.save()
    return competition.current_game.as_map()


def display():
    return competition.current_game.display_map()


def score(ace, first_team, first_player):
    if first_team:
        competition.current_game.team_one.add_score(first_player, ace)
    else:
        competition.current_game.team_two.add_score(first_player, ace)
    competition.current_game.print_gamestate()
    return "", 204


def start(swap, swapTeamOne, swapTeamTwo):
    competition.current_game.start(swap, swapTeamOne, swapTeamTwo)
    competition.current_game.print_gamestate()
    return "", 204


def end(best_player):
    competition.current_game.end(best_player)
    competition.current_game.print_gamestate()
    return "", 204


def timeout(first_team):
    if first_team:
        competition.current_game.team_one.call_timeout()
    else:
        competition.current_game.team_two.call_timeout()
    competition.current_game.print_gamestate()
    return "", 204


def undo():
    competition.current_game.undo()
    competition.current_game.print_gamestate()
    return "", 204


def card(color, first_team, first_player, time=3):
    if first_team:
        if color == "green":
            competition.current_game.team_one.green_card(first_player)
        elif color == "yellow":
            competition.current_game.team_one.yellow_card(first_player, time)
        elif color == "red":
            competition.current_game.team_one.red_card(first_player)
    else:
        if color == "green":
            competition.current_game.team_two.green_card(first_player)
        elif color == "yellow":
            competition.current_game.team_two.yellow_card(first_player, time)
        elif color == "red":
            competition.current_game.team_two.red_card(first_player)
    competition.current_game.print_gamestate()
    return "", 204


start(False, False, False)
score(False, True, True)
score(False, True, True)
score(False, True, True)
card("red", True, True)
undo()
card("red", True, True)
card("red", True, False)
end("Olivia Stronach")
start(False, False, False)
undo()
undo()
undo()
undo()
score(False, True, True)
score(False, True, True)
score(False, True, True)
card("red", True, True)
card("yellow", True, False)
print([i.fixture_to_table_row() for i in competition.fixtures])
