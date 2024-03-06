from test import *

competition = comps["fourth_suss_championship"]

best_so_far = -1

#
# def check(competition):
#     global best_so_far
#     target_ladder = ["officials", "whipped", "satnavs", "seanitha", "idk", "barbenheimer", "tradies", "ikea_workers",
#                      "sleeby"]
#
#     ladders = [i.nice_name() == j for i, j in zip(competition.ladder(), target_ladder)]
#     print(f"{9 - sum(ladders)} teams were wrong (best {9 - best_so_far})")
#     if sum(ladders) > best_so_far:
#         competition.save("./config/tournaments/best.json")
#         print("That was our best tournament so far, saving to best")
#         best_so_far = sum(ladders)
#     return all(ladders)


def check(competition):
    print(f"Winner is {competition.ladder()[0]}")
    return competition.ladder()[0].nice_name() == "bedwars_besties"


if __name__ == "__main__":
    random = Random()
    logger.setLevel(logging.CRITICAL)

    def r_bool():
        return bool(random.randint(0, 1))

    once = False
    winners = False
    while not once or not check(competition):
        once = True
        competition.dump()
        game_id = 0
        game_count = 40
        competition.get_game(game_id).start(r_bool(), r_bool(), r_bool())
        while not competition.in_finals:
            game = competition.get_game(game_id)
            if game.bye:
                game_id += 1
                competition.get_game(game_id).start(r_bool(), r_bool(), r_bool())
                continue
            print(game_id)
            if competition.get_game(game_id).game_ended():
                game.end(game.current_players[0].name)
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
    print("-" * 20)
    for i, t in enumerate(sorted(competition.teams, key=lambda a: -a.games_won)):
        print(f"{i + 1}: {t.name} [{t.first_ratio()}] [{t.court_one}]")
    print("-" * 20)
    for t in competition.officials:
        print(f": {t.name} [{t.games_court_one / t.games_umpired}] <{t.internal_games_scored}>")
    print("-" * 20)
    app.run(host="0.0.0.0", port=80, debug=True, use_reloader=False)
