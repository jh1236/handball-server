import itertools
import math


K = 40.0
initial_elo = 1500
D = 3000.0


numbers = {0: "One", 1: "Two", 2: "Three", 3: "Four"}


def probability(other, me):
    return 1.0 / (1.0 + math.pow(10, K * (other - me) / D))


def calc_elo(elo, elo_other, first_won):
    pa = probability(elo_other, elo)
    ra = K * (first_won - pa)
    return ra


def get_player_stats_categories(stats):
    out = {
        "Serving": {
            "Points served": stats["Points served"],
            "Aces scored": stats["Aces scored"],
            "Faults": stats["Faults"],
            "Double Faults": stats["Double Faults"],
            "Aces Per Game": stats["Aces Per Game"],
            "Faults Per Game": stats["Faults Per Game"],
            "Serves Per Ace": stats["Serves Per Ace"],
            "Serves Per Fault": stats["Serves Per Fault"],
            "Serve Ace Rate": stats["Serve Ace Rate"],
            "Serve Fault Rate": stats["Serve Fault Rate"],
            "Serving Conversion Rate": stats["Serving Conversion Rate"],
            "Average Serving Streak": stats["Average Serving Streak"],
            "Max. Serving Streak": stats["Max. Serving Streak"],
            "Max. Ace Streak": stats["Max. Ace Streak"],
            "Serves Received": stats["Serves Received"],
        },
        "Misconduct": {
            "Green Cards": stats["Green Cards"],
            "Yellow Cards": stats["Yellow Cards"],
            "Red Cards": stats["Red Cards"],
            "Cards": stats["Cards"],
            "Rounds Carded": stats["Rounds Carded"],
            "Cards Per Game": stats["Cards Per Game"],
            "Points Per Card": stats["Points Per Card"],
        },
        "Game Performance": {
            "B&F Votes": stats["B&F Votes"],
            "Elo": stats["Elo"],
            "Games Played": stats["Games Played"],
            "Games Won": stats["Games Won"],
            "Percentage": stats["Percentage"],
            "Net Elo Delta": stats["Net Elo Delta"],
            "Average Elo Delta": stats["Average Elo Delta"],
            "Votes Per 100 Games": stats["Votes Per 100 Games"],
        },
        "Point Performance": {
            "Points scored": stats["Points scored"],
            "Rounds on Court": stats["Rounds on Court"],
            "Points Per Game": stats["Points Per Game"],
            "Percentage of Points scored": stats["Percentage of Points scored"],
            "Serves Returned": stats["Serves Returned"],
            "Return Rate": stats["Return Rate"],
        },
    }
    return out


def get_player_stats(tournament, player, detail=0, team=None):
    from website.website import sign

    games = []
    game_players = []
    if tournament:
        tournaments = [tournament]
    else:
        from start import comps

        tournaments = comps.values()

    for t in tournaments:
        if player is None:
            games += t.games_to_list()
            game_players += sum([i.playing_players for i in t.games_to_list()], [])
            continue
        for i in t.games_to_list():
            player_names = [j.name for j in i.teams[0].players] + [
                j.name for j in i.teams[1].players
            ]
            players = i.teams[0].players + i.teams[1].players
            if (
                player.name in player_names
                and (
                    i.ranked
                    or (tournament and not tournament.details.get("ranked", True))
                )
                and (not team or team.nice_name() in [j.nice_name() for j in i.teams])
                and i.started
                and not i.bye
            ):
                games.append(i)
                game_players.append(players[player_names.index(player.name)])
    played = len(game_players)
    points_scored = sum([i.points_scored for i in game_players])
    aces_scored = sum([i.aces_scored for i in game_players])
    green_cards = sum([i.green_cards for i in game_players])
    yellow_cards = sum([i.yellow_cards for i in game_players])
    red_cards = sum([i.red_cards for i in game_players])
    time_on_court = sum([i.time_on_court for i in game_players])
    time_carded = sum([i.time_carded for i in game_players])
    faults = sum([i.faults for i in game_players])
    double_faults = sum([i.double_faults for i in game_players])

    wins = (
        played
        if not player
        else len(
            [
                i
                for i in games
                if player.nice_name() in [j.nice_name() for j in i.winner.players]
            ]
        )
    )
    served = sum([i.points_served for i in game_players])
    won_while_serving = sum([i.won_while_serving for i in game_players])
    votes = (
        len(
            [
                i
                for i in games
                if i.best_player and i.best_player.nice_name() == player.nice_name()
            ]
        )
        if player
        else played
    )
    out = {
        "B&F Votes": votes,
        "Elo": "-" if not player else round(player.elo, 2),
        "Peak Elo": round(max([i.elo_at_start for i in game_players ]+ [0]), 2),
        "Points Scored": points_scored,
        "Aces Scored": aces_scored,
        "Faults": faults,
        "Double Faults": double_faults,
        "Green Cards": green_cards,
        "Yellow Cards": yellow_cards,
        "Red Cards": red_cards,
        "Rounds Played": time_on_court,
        "Rounds Carded": time_carded,
        "Games Played": played,
        "Games Won": wins,
    }
    if not detail:
        return out
    serving_streaks = []
    for i in game_players:
        serving_streaks += i.serve_streak
    ace_streak = []
    for i in game_players:
        ace_streak += i.ace_streak
    avg_streak_len = sum(serving_streaks) / (len(serving_streaks) or 1)
    max_streak_len = max(serving_streaks + [0])
    max_ace_streak = max(ace_streak + [0])
    serves_received = sum(i.serves_received for i in game_players)
    serves_returned = sum(i.serve_return for i in game_players)
    total_elo_delta = sum(i.elo_delta for i in game_players if i.elo_delta)
    avg_elo_delta = sum(i.elo_delta for i in game_players if i.elo_delta) / (
        len(game_players) or 1
    )
    points_per_loss = points_scored / ((played - wins) or 1)
    points_scored_by_team = sum(i.team.score for i in game_players)
    cards = green_cards + yellow_cards + red_cards
    left = (
        len(
            [
                i
                for i in games
                if player.nice_name() in [j.players[0].nice_name() for j in i.teams]
            ]
        )
        if player
        else 0
    )
    out |= {
        "Percentage": f"{100 * (wins / (played or 1)):.1f}%",
        "Net Elo Delta": f"{sign(total_elo_delta)}{abs(total_elo_delta):.2f}",
        "Average Elo Delta": f"{sign(avg_elo_delta)}{abs(avg_elo_delta):.2f}",
        "Points Served": served,
        "Points Per Game": round(points_scored / (played or 1), 2),
        "Points Per Loss": "∞" if wins == played else round(points_per_loss, 2),
        "Aces Per Game": round(aces_scored / (played or 1), 2),
        "Faults Per Game": round(faults / (played or 1), 2),
        "Cards Per Game": round(cards / (played or 1), 2),
        "Cards": cards,
        "Points Per Card": "∞" if not cards else round(time_on_court / cards, 2),
        "Serves Per Ace": "∞" if not aces_scored else round(served / aces_scored, 2),
        "Serves Per Fault": "∞" if not faults else round(served / faults, 2),
        "Serve Ace Rate": f"{aces_scored / (served or 1) * 100:.1f}%",
        "Serve Fault Rate": f"{faults / (served or 1) * 100: .1f}%",
        "Percentage of Points Scored": f"{points_scored / ((time_on_court + time_carded) or 1) * 100:.1f}%",
        "Percentage of Points Scored for Team": f"{points_scored / (points_scored_by_team or 1) * 100:.1f}%",
        "Percentage of Games as Left Player": f"{left / (played or 1) * 100:.1f}%",
        "Serving Conversion Rate": f"{won_while_serving / (served or 1) * 100:.1f}%",
        "Average Serving Streak": round(avg_streak_len, 2),
        "Max. Serving Streak": max_streak_len,
        "Max. Ace Streak": max_ace_streak,
        "Serves Received": serves_received,
        "Serves Returned": serves_returned,
        "Serves Missed": serves_received - serves_returned,
        "Return Rate": f"{100 *serves_returned / (serves_received or 1):.1f}%",
        "Serves Missed Per Game": round(
            (serves_received - serves_returned) / (played or 1), 2
        ),
        "Votes Per 100 Games": round(votes * 100 / (played or 1), 1),
    }
    if detail == 1:
        return out
    for j in range(2):
        court_games = [i for i in games if i.court == j]
        if player is not None:

            court_players = [
                next(
                    k
                    for k in i.teams[0].players + i.teams[1].players
                    if player.nice_name() == k.nice_name()
                )
                for i in court_games
            ]
        else:
            court_players = sum((i.current_players for i in court_games), [])
        court_wins = (
            len(
                [
                    i
                    for i in court_games
                    if player.nice_name() in [j.nice_name() for j in i.winner.players]
                ]
            )
            if player
            else played
        )
        court_points_scored = sum([i.points_scored for i in court_players])
        court_aces_scored = sum([i.aces_scored for i in court_players])
        court_green_cards = sum([i.green_cards for i in court_players])
        court_yellow_cards = sum([i.yellow_cards for i in court_players])
        court_red_cards = sum([i.red_cards for i in court_players])
        court_time_on_court = sum([i.time_on_court for i in court_players])
        court_time_carded = sum([i.time_carded for i in court_players])
        court_faults = sum([i.faults for i in court_players])
        court_double_faults = sum([i.double_faults for i in court_players])
        court_played = len(court_players)
        court_served = sum([i.points_served for i in court_players])
        court_won_while_serving = sum([i.won_while_serving for i in court_players])
        court_points_scored_by_team = sum(i.team.score for i in game_players)

        court_votes = (
            len(
                [
                    i
                    for i in games
                    if i.best_player
                    and i.best_player.nice_name() == player.nice_name()
                    and i.court == j
                ]
            )
            if player
            else played
        )
        court_left = (
            len(
                [
                    i
                    for i in court_games
                    if player.nice_name() in [j.players[0].nice_name() for j in i.teams]
                ]
            )
            if player
            else 0
        )
        court_cards = court_red_cards + court_yellow_cards + court_green_cards
        court_serves_received = sum(i.serves_received for i in court_players)
        court_serves_returned = sum(i.serve_return for i in court_players)
        serving_streaks = []
        for i in court_players:
            serving_streaks += i.serve_streak
        ace_streak = []
        for i in court_players:
            ace_streak += i.ace_streak
        serving_streaks = [i for i in serving_streaks if i]
        court_avg_streak_len = sum(serving_streaks) / (len(serving_streaks) or 1)
        court_max_streak_len = max(serving_streaks + [0])
        court_max_ace = max(ace_streak + [0])
        court_elo_delta = sum(i.elo_delta for i in court_players if i.elo_delta)
        court_avg_elo_delta = sum(i.elo_delta for i in court_players if i.elo_delta) / (
            len(court_players) or 1
        )
        court_points_per_loss = court_points_scored / ((court_played - court_wins) or 1)

        out |= {
            f"Court {numbers[j]}": {
                "B&F Votes": court_votes,
                "Points Scored": court_points_scored,
                "Aces Scored": court_aces_scored,
                "Faults": court_faults,
                "Double Faults": court_double_faults,
                "Green Cards": court_green_cards,
                "Yellow Cards": court_yellow_cards,
                "Red Cards": court_red_cards,
                "Rounds on Court": court_time_on_court,
                "Rounds Carded": court_time_carded,
                "Games Played": court_played,
                "Games Won": court_wins,
                "Percentage": f"{100 * (court_wins / (court_played or 1)):.1f}%",
                "Net Elo Delta": f"{sign(court_elo_delta)}{abs(court_elo_delta):.2f}",
                "Average Elo Delta": f"{sign(court_avg_elo_delta)}{abs(court_avg_elo_delta):.2f}",
                "Points Served": court_served,
                "Points Per Game": round(court_points_scored / (court_played or 1), 2),
                "Points Per Loss": "∞"
                if wins == played
                else round(court_points_per_loss, 2),
                "Aces Per Game": round(court_aces_scored / (court_played or 1), 2),
                "Faults Per Game": round(court_faults / (court_played or 1), 2),
                "Cards Per Game": round(court_cards / (court_played or 1), 2),
                "Cards": court_cards,
                "Points Per Card": "∞"
                if not court_cards
                else round(court_time_on_court / court_cards, 2),
                "Serves Per Ace": "∞"
                if not court_aces_scored
                else round(court_served / court_aces_scored, 2),
                "Serves Per Fault": "∞"
                if not court_faults
                else round(court_served / court_faults, 2),
                "Serve Ace Rate": f"{court_aces_scored / (court_served or 1) * 100:.1f}%",
                "Serve Fault Rate": f"{court_faults / (court_served or 1) * 100:.1f}%",
                "Percentage of Points Scored": f"{court_points_scored / ((court_time_on_court + court_time_carded) or 1) * 100: .1f}%",
                "Percentage of Points Scored for Team": f"{court_points_scored / (court_points_scored_by_team or 1) * 100: .1f}%",
                "Percentage of Games as Left Player": f"{court_left / (court_played or 1) * 100:.1f}%",
                "Serving Conversion Rate": f"{court_won_while_serving / (court_served or 1) * 100:.1f}%",
                "Average Serving Streak": round(court_avg_streak_len, 2),
                "Max. Serving Streak": court_max_streak_len,
                "Max. Ace Streak": court_max_ace,
                "Serves Received": court_serves_received,
                "Serves Returned": court_serves_returned,
                "Serves Missed": court_serves_received - court_serves_returned,
                "Return Rate": f"{100 * court_serves_returned / (court_serves_received or 1):.1f}%",
                "Serves Missed Per Game": round(
                    (court_serves_received - court_serves_returned) / (played or 1), 2
                ),
                "Votes Per 100 Games": round(
                    court_votes * 100 / (court_played or 1), 1
                ),
            }
        }
    return out


def team_stats(tournament, team, include_players=False):
    games = []
    game_teams = []
    if tournament:
        tournaments = [tournament]
    else:
        from start import comps

        tournaments = comps.values()

    for t in tournaments:
        for i in t.games_to_list():
            team_names = [j.name for j in i.teams]
            if (
                team.name in team_names
                and i.started
                and not i.bye
                and (
                    i.ranked
                    or (tournament and not tournament.details.get("ranked", True))
                )
            ):
                games.append(i)
                game_teams.append(i.teams[team_names.index(team.name)])

    points_for = sum([i.score for i in game_teams])
    points_against = sum([i.opponent.score for i in game_teams])
    games_won = len([i for i in games if i.winner.nice_name() == team.nice_name()])
    dif = points_for - points_against
    green_cards = sum([i.green_cards for i in game_teams])
    yellow_cards = sum([i.yellow_cards for i in game_teams])
    red_cards = sum([i.red_cards for i in game_teams])
    timeouts = sum([(1 - i.timeouts) for i in game_teams])
    faults = sum([i.faults for i in game_teams])
    games_played = len(game_teams)
    d = {
        "Elo": round(team.elo, 2),
        "Games Played": games_played,
        "Games Won": games_won,
        "Games Lost": games_played - games_won,
        "Percentage": f"{100 * (games_won / games_played): .1f}%"
        if games_played > 0
        else "-",
        "Green Cards": green_cards,
        "Yellow Cards": yellow_cards,
        "Red Cards": red_cards,
        "Faults": faults,
        "Timeouts Called": timeouts,
        "Points For": points_for,
        "Points Against": points_against,
        "Point Difference": dif,
    }
    if include_players:
        d["players"] = [
            {"name": i.name} | get_player_stats(tournament, i, team=team, detail=1)
            for i in team.players
        ]
    return d
