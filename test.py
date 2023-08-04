import tournaments
from tournaments.Tournament import Tournament

competition: Tournament = tournaments.Swiss.load()

print(competition.teams)

def teams():
    return {i.name: i.as_map() for i in competition.teams}

def games():
    competition.save()
    return competition.current_game.as_map()

def display():
    return competition.current_game.display_map()

def score(ace, first_team, left_player):
    if first_team:
        competition.current_game.team_one.add_score(left_player, ace)
    else:
        competition.current_game.team_two.add_score(left_player, ace)
    competition.current_game.print_gamestate()

def start(swap:bool = False):
    competition.current_game.start(swap)
    competition.current_game.print_gamestate()

def timeout(first_team):
    if first_team:
        competition.current_game.team_one.call_timeout()
    else:
        competition.current_game.team_two.call_timeout()
    competition.current_game.print_gamestate()

def card(color, first_team, left_player, time=3):
    if first_team:
        if color == "green":
            competition.current_game.team_one.green_card(left_player)
        elif color == "yellow":
            competition.current_game.team_one.yellow_card(left_player, time)
        elif color == "red":
            competition.current_game.team_one.red_card(left_player)
    else:
        if color == "green":
            competition.current_game.team_two.green_card(left_player)
        elif color == "yellow":
            competition.current_game.team_two.yellow_card(left_player, time)
        elif color == "red":
            competition.current_game.team_two.red_card(left_player)
    competition.current_game.print_gamestate()

def site():
    with open("./resources/site.html") as fp:
        string = fp.read()
    repl = "\n".join([j.fixture_to_table_row() for j in competition.fixtures])
    string = string.replace("%replace%", repl)

    return string

competition.print_ladder()
card("red", True, True)