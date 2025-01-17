# raise Exception("THIS WILL DELETE THE DATABASE! DO NOT RUN THIS UNLESS YOU WANT TO DELETE THE DATABASE\nif for whatever reason you want to reconstruct the database from json files, run this script in the root directory of the project and rem out this exception, also good luck!")

import json
import os

from FixtureMakers.Pooled import Pooled
from structure.Tournament import load_all_tournaments
from structure.UniversalTournament import get_all_players, get_all_officials, get_all_teams
from structure.structureNew import RiggedGame
from utils.databaseManager import DatabaseManager
from utils.util import n_chunks

practice = None
practice_round = 1
practice_teams = []
practice_officials = []


def process_game_string(game, tournament):
    game.load_from_string = lambda a: RiggedGame.load_from_string(game, a, s, tournament)
    game.reload()


def process_game(tournamentId, game, round, isRanked):
    servingTeam = s.execute("SELECT id FROM teams WHERE name = ?", (game.teams[0].name,)).fetchone()[0]
    receivingTeam = s.execute("SELECT id FROM teams WHERE name = ?", (game.teams[1].name,)).fetchone()[0]
    if servingTeam == receivingTeam:
        return
    if not game.first_team_serves:
        servingTeam, receivingTeam = receivingTeam, servingTeam

    bestPlayer = "Null"  # default
    if game.best_player and (game.best_player.name not in ("Good bye", "Forfeit")):  # Angri boi
        bestPlayer = game.best_player.name
    bestPlayer = s.execute("SELECT id FROM people WHERE name = ?", (bestPlayer,)).fetchone()[0]

    official = scorer = None
    if game.primary_official.name != "No one":  # this confused the hell out of me
        official = s.execute("""
                SELECT officials.id 
                FROM officials 
                JOIN people ON officials.personId = people.id 
                WHERE people.name = ?
                """,
                             (game.primary_official.name,)).fetchone()[0]
        if game.scorer.name != "No one":
            scorer = s.execute("""
                SELECT officials.id 
                FROM officials 
                JOIN people ON officials.personId = people.id 
                WHERE people.name = ?
                """,
                               (game.scorer.name,)).fetchone()[0]

    gameString = game.game_string
    started = game.started
    startTime = game.start_time
    length = game.length
    court = game.court
    protested = game.protested
    resolved = game.resolved
    isFinal = game.is_final
    notes = game.notes
    isBye = game.bye or game.super_bye
    status = game.status_string
    adminStatus = game.noteable_string(True)
    winning_team = s.execute("SELECT id FROM teams WHERE name = ?", (game.winner.name,)).fetchone()[0]

    ranked = game.ranked

    s.execute(
        """INSERT INTO games (
            tournamentId, teamOne, teamTwo, bestPlayer, official, scorer, gameStringVersion,  gameString, startTime, length, court, isFinal, round, notes, isBye, status, adminStatus, isRanked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (tournamentId, servingTeam, receivingTeam, bestPlayer, official, scorer, 1, gameString, startTime,
         length, court,
         isFinal, round, notes, isBye, status, adminStatus, ranked)
    )

    if not (game.bye or game.is_final):
        s.execute("UPDATE tournamentTeams SET gamesPlayed = gamesPlayed + 1 WHERE teamId = ? AND tournamentId = ?",
                  (servingTeam, tournamentId))
        s.execute("UPDATE tournamentTeams SET gamesPlayed = gamesPlayed + 1 WHERE teamId = ? AND tournamentId = ?",
                  (receivingTeam, tournamentId))
        s.execute("UPDATE tournamentTeams SET gamesWon = gamesWon + 1 WHERE teamId = ? AND tournamentId = ?",
                  (winning_team, tournamentId))
        s.execute("UPDATE tournamentTeams SET gamesLost = gamesLost + 1 WHERE teamId = ? AND tournamentId = ?",
                  (servingTeam if winning_team == receivingTeam else receivingTeam, tournamentId))

    for team in game.teams:
        timeoutsCalled = 1 - team.timeouts
        s.execute(
            "UPDATE tournamentTeams SET timeoutsCalled = timeoutsCalled + ? WHERE teamId = (SELECT id FROM teams WHERE name = ?) AND tournamentId = ?",
            (timeoutsCalled, team.name, tournamentId))

    game_id = s.execute("SELECT id FROM games ORDER BY id DESC LIMIT 1").fetchone()[0]

    for player in game.playing_players:
        if player.name not in ("Good bye", "Forfeit"):
            # gameId INTEGER, +
            # playerId INTEGER,
            playerId = s.execute("SELECT id FROM people WHERE name = ?", (player.name,)).fetchone()[0]
            # teamId INTEGER,
            teamId = s.execute("SELECT id FROM teams WHERE name = ?", (player.team.name,)).fetchone()[0]
            # opponentId INTEGER
            otherTeam = [i for i in game.teams if not i.name == player.team.name][0].name
            opponentId = s.execute("SELECT id FROM teams WHERE name = ?", (otherTeam,)).fetchone()[0]
            # tournamentId INTEGER, +
            # cardTime INTEGER,
            cardTime = player.card_duration  # mmm consistency
            # cardTimeRemaining INTEGER,
            cardTimeRemaining = player.card_time_remaining
            # roundsPlayed INTEGER,
            roundPlayed = player.time_on_court
            # roundsBenched INTEGER,
            roundsBenched = player.time_carded
            # isBestPlayer INTEGER,
            isBestPlayer = player.best
            # isFinal INTEGER, +
            sideOfCourt = ["Left", "Right", "Substitute"][player.team.players.index(player)]
            s.execute(
                """INSERT INTO playerGameStats (
                    gameId,   playerId, teamId, opponentId, tournamentId,roundsPlayed, roundsBenched, isBestPlayer, startSide, isFinal
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (game_id, playerId, teamId, opponentId, tournamentId, roundPlayed, roundsBenched, isBestPlayer,
                 sideOfCourt, isFinal)
            )

            if isRanked and (not isFinal) and player.elo_delta:
                # gameId INTEGER,
                # playerId INTEGER,
                # eloChange INTEGER

                eloChange = player.elo_delta
                s.execute(
                    "INSERT INTO eloChange (gameId, playerId, eloChange, tournamentId) VALUES (?, ?, ?, ?)",
                    (game_id, playerId, eloChange, tournamentId)
                )

    process_game_string(game, tournamentId)

    s.execute("""UPDATE games
SET teamOneScore    = lg.teamOneScore,
    teamTwoScore    = lg.teamTwoScore,
    teamOneTimeouts = lg.teamOneTimeouts,
    teamTwoTimeouts = lg.teamTwoTimeouts,
    winningTeam     = lg.winningTeam,
    started         = lg.started,
    ended           = lg.ended,
    protested       = lg.protested,
    someoneHasWon   = lg.someoneHasWon,
    resolved        = lg.resolved,
    playerToServe = lg.playerToServe,
    teamToServe = lg.teamToServe,
    sideToServe = lg.sideToServe
FROM liveGames lg
WHERE lg.id = games.id AND games.id = ?""", (game_id,))

    s.execute("""UPDATE playerGameStats
SET points = lg.points,
    aces = lg.aces,
    faults = lg.faults,
    servedPoints = lg.servedPoints,
    servedPointsWon = lg.servedPointsWon,
    servesReceived = lg.servesReceived,
    servesReturned = lg.servesReturned,
    doubleFaults = lg.doubleFaults,
    greenCards = lg.greenCards,
    warnings = lg.warnings,
    yellowCards = lg.yellowCards,
    redCards = lg.redCards,
    cardTimeRemaining = lg.cardTimeRemaining,
    cardTime = lg.cardTime
FROM livePlayerGameStats lg
WHERE playerGameStats.id = lg.id
        AND playerGameStats.gameId = ?""", (game_id,))

    if (game_id % 10 == 0):
        print(f"completed Game {game_id}")


if __name__ == "__main__":
    database_file = 'resources/database.db'
    if os.path.exists(database_file):
        os.remove(database_file)

    with DatabaseManager(force_create_tables=True) as s:
        s.execute("""drop trigger updateGames;""")
        comp = load_all_tournaments()

        with open("./resources/taunts.json", "r") as f:
            for key, items in json.load(f).items():
                for item in items:
                    s.execute("INSERT INTO taunts (event, taunt) VALUES (?, ?)", (key, item))

        for player in get_all_players():
            s.execute("INSERT INTO people (name, searchableName) VALUES (?, ?)", (player.name, player.nice_name()))

        for official in get_all_officials():
            s.execute("SELECT id FROM people WHERE name = ?", (official.name,))
            oid = s.fetchone()[0]
            s.execute("INSERT INTO officials (personId, isAdmin, proficiency) VALUES (?, ?, ?)",
                      (oid, official.admin, official.level))
            s.execute("UPDATE people SET password = ? WHERE id = ?", (official.key, oid))
        # add BYE team
        name = "BYE"
        nullPlayer = s.execute("SELECT id FROM people WHERE name = ?", ("Null",)).fetchone()[0]
        s.execute("INSERT INTO teams (name, captain) VALUES (?, ?)", (name, nullPlayer))
        for team in get_all_teams():
            # id INTEGER PRIMARY KEY AUTOINCREMENT,
            # name TEXT,
            # searchableName TEXT,
            # imageURL TEXT,
            # primaryColour INTEGER,
            # secondaryColour INTEGER,
            # imageURL TEXT,

            # captain INTEGER,
            # nonCaptain INTEGER,
            # substitute INTEGER,

            searchableName = team.nice_name()
            name = team.name
            imageURL = team.image_path
            primaryColor = team.primary_color
            secondaryColor = team.secondary_color

            captain = s.execute("SELECT id FROM people WHERE name = ?", (team.captain.name,)).fetchone()[0]
            s.execute(
                "INSERT INTO teams (name, searchableName, imageURL, primaryColor, secondaryColor, captain) VALUES (?, ?, ?, ?, ?, ?)",
                (name, searchableName, imageURL, primaryColor, secondaryColor, captain))
            if team.non_captain.name != "Null":
                # get the most recent team
                team_id = s.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 1").fetchone()[
                    0]  # get the most recent team
                nonCaptain = s.execute("SELECT id FROM people WHERE name = ?", (team.non_captain.name,)).fetchone()[0]
                s.execute("UPDATE teams SET nonCaptain = ? WHERE id = ?", (nonCaptain, team_id))

            if len(team.players) > 2 and team.players[2].name != "Null":
                substitute = s.execute("SELECT id FROM people WHERE name = ?", (team.players[2].name,)).fetchone()[0]
                s.execute("UPDATE teams SET substitute = ? WHERE id = ?", (substitute, team_id))

        for tournament in sorted(comp.values(), key=lambda a: "practice_season_one" not in a.nice_name()):
            # create_tournaments_table = """CREATE TABLE IF NOT EXISTS tournaments (
            #     id INTEGER PRIMARY KEY AUTOINCREMENT,
            #     finalsGenerator TEXT,
            #     fixturesGenerator TEXT,
            #     name TEXT,
            #     ranked INTEGER,
            #     twoCourts INTEGER,
            #     notes STRING,
            #     logoURL STRING
            # );"""

            # # officials and teams is stored as sum(2**[officials/teams](id)) for each official/team in the tournament
            # # to get official or team for a tournament, do a bitwise AND with 2**[officials/teams](id) and tournaments([officials/teams])

            # # kept as string because of int size limitations
            # # will have a parse function so this is never revealed but here is the reasoning if someone ever looks at this
            # # in the backend for whatever reason
            finalsGenerator = tournament.finals_class.get_name()
            fixturesGenerator = tournament.fixtures_class.get_name()
            name = tournament.name
            searchableName = tournament.nice_name()
            ranked = tournament.details.get("ranked", True)
            isPooled = isinstance(tournament.fixtures_class, Pooled)
            hasScorer = tournament.details.get("scorer", False)

            notes = tournament.notes

            twoCourts = tournament.two_courts
            if "practice" in tournament.nice_name():
                if practice is None:
                    s.execute(
                        "INSERT INTO tournaments (searchableName, finalsGenerator, fixturesGenerator, name, ranked, twoCourts, notes, isPooled, imageURL, hasScorer, isFinished, inFinals) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)",
                        (searchableName, finalsGenerator, fixturesGenerator, name, ranked, twoCourts, notes, isPooled,
                         f"/api/tournaments/image?name={searchableName}")
                    )
                    practice = s.execute("SELECT id FROM tournaments ORDER BY id DESC LIMIT 1").fetchone()[0]
                tournamentId = practice
            else:
                s.execute(
                    "INSERT INTO tournaments (searchableName, finalsGenerator, fixturesGenerator, name, ranked, twoCourts, notes, isPooled, imageURL, hasScorer, isFinished, inFinals) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)",
                    (searchableName, finalsGenerator, fixturesGenerator, name, ranked, twoCourts, notes, isPooled,
                     f"/api/tournaments/image?name={searchableName}", hasScorer)
                )
                tournamentId = s.execute("SELECT id FROM tournaments ORDER BY id DESC LIMIT 1").fetchone()[0]
            # id INTEGER PRIMARY KEY AUTOINCREMENT,
            # tournamentId INTEGER,
            # servingTeam INTEGER,
            # receivingTeam INTEGER,
            # bestPlayer INTEGER,
            # official INTEGER,
            # scorer INTEGER,
            # IGASide INTEGER,
            # gameStringVersion INTEGER,
            # teamOneScore INTEGER,
            # teamTwoScore INTEGER,
            # gameString TEXT,
            # started INTEGER,
            # startTime INTEGER,
            # length INTEGER,
            # court INTEGER,
            # protested INTEGER,
            # resolved INTEGER,
            # isFinal INTEGER,
            # notes TEXT,

            pools = None
            if isinstance(tournament.fixtures_class, Pooled):
                pools = [*n_chunks(sorted(tournament.teams, key=lambda it: it.nice_name()), 2)]
            for t in tournament.teams:
                if "practice" in tournament.nice_name():
                    if t.nice_name() in practice_teams:
                        continue
                    else:
                        practice_teams.append(t.nice_name())
                s.execute("SELECT id FROM teams WHERE name = ?", (t.name,))
                team = s.fetchone()[0]
                pool = None if pools is None else (int(t.name in [i.name for i in pools[1]]) + 1)

                s.execute(
                    "INSERT INTO tournamentTeams (tournamentId, teamId, gamesWon, gamesLost, gamesPlayed, timeoutsCalled, pool) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (tournamentId, team, 0, 0, 0, 0, pool))

            for official in tournament.officials:
                if "practice" in tournament.nice_name():
                    if official.nice_name() in practice_teams:
                        continue
                    else:
                        practice_officials.append(t.nice_name())
                official_id = \
                    s.execute("SELECT id FROM officials WHERE personId = (SELECT id FROM people WHERE name = ?)",
                              (official.name,)).fetchone()[0]
                s.execute(
                    "INSERT INTO tournamentOfficials (tournamentId, officialId, isUmpire, isScorer) VALUES (?, ?, ?, ?)",
                    (tournamentId, official_id, 1, 1))

            if "practice" in tournament.nice_name():
                round = practice_round
            else:
                round = 1

            for roundgames in tournament.fixtures:
                for game in roundgames:
                    process_game(tournamentId, game, round, ranked)
                round += 1
            for roundgames in tournament.finals:
                for game in roundgames:
                    process_game(tournamentId, game, round, ranked)
                round += 1
            if "practice" in tournament.nice_name():
                practice_round = round

    with DatabaseManager(force_create_tables=True) as c:
        c.execute("""UPDATE tournaments SET name = 'SUSS Practice', searchableName = 'suss_practice', imageURL = '/api/tournaments/image?name=suss_practice', fixturesGenerator = 'OneRoundEditable' WHERE tournaments.id = 1""")
