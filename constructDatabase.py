# raise Exception("THIS WILL DELETE THE DATABASE! DO NOT RUN THIS UNLESS YOU WANT TO DELETE THE DATABASE\nif for whatever reason you want to reconstruct the database from json files, run this script in the root directory of the project and rem out this exception, also good luck!")
from utils.databaseManager import DatabaseManager
from structure.Tournament import load_all_tournaments
from structure.UniversalTournament import get_all_players, get_all_officials, get_all_teams
import os


def process_game(tournamentId, game, round, isFinal):
    servingTeam = s.execute("SELECT id FROM teams WHERE name = ?", (game.teams[0].name,)).fetchone()[0]
    receivingTeam = s.execute("SELECT id FROM teams WHERE name = ?", (game.teams[1].name,)).fetchone()[0]
    servingScore = game.teams[0].score
    receivingScore = game.teams[1].score
    
    if not game.first_team_serves:
        servingTeam, receivingTeam = receivingTeam, servingTeam
        servingScore, receivingScore = receivingScore, servingScore
    
    bestPlayer = "Null" # default
    if game.best_player and (game.best_player.name not in ("Good bye", "Forfeit")): #Angri boi
        bestPlayer = game.best_player.name
    bestPlayer = s.execute("SELECT id FROM people WHERE name = ?", (bestPlayer,)).fetchone()[0]
    
    official = scorer = None
    if game.primary_official.name != "No one": # this confused the hell out of me
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
    s.execute(
        """INSERT INTO games (
            tournamentId, servingTeam, receivingTeam, bestPlayer, official, scorer, gameStringVersion, servingScore, receivingScore, gameString, started, startTime, length, court, protested, resolved, isFinal, round, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tournamentId, servingTeam, receivingTeam, bestPlayer, official, scorer, 1,                servingScore, receivingScore, gameString, started, startTime, length, court, protested, resolved, isFinal, round, notes)
    )
    
    
    for card in game.cards:
        # id INTEGER PRIMARY KEY AUTOINCREMENT,
        # personId INTEGER,
        # officialId INTEGER,
        # gameId INTEGER,
        # type STRING,
        # reason STRING,
        player = s.execute("SELECT id FROM people WHERE name = ?", (card.player.name,)).fetchone()[0]
        game_id = s.execute("SELECT id FROM games ORDER BY id DESC LIMIT 1").fetchone()[0]
        color = card.color
        length = card.duration
        reason = card.reason
        s.execute(
            "INSERT INTO punishments (personId, officialId, gameId, color, length, reason) VALUES (?, ?, ?, ?, ?, ?)",
            (player, official, game_id, color, length, reason)
        )
    
if __name__ == "__main__":
    database_file = './resources/database.db'
    if os.path.exists(database_file):
        os.remove(database_file)
        
    if os.path.exists(database_file):
        raise("Database exists! this is meant to be a fresh start!")

    with DatabaseManager() as s:
        comp = load_all_tournaments()
        for player in get_all_players():
            s.execute("INSERT INTO people (name) VALUES (?)", (player.name,))

        for official in get_all_officials():
            s.execute("SELECT id FROM people WHERE name = ?", (official.name,))
            oid = s.fetchone()[0]
            s.execute("INSERT INTO officials (personId, isAdmin, proficiency) VALUES (?, ?, ?)", (oid,official.admin,official.level))
            s.execute("UPDATE people SET password = ? WHERE id = ?", (official.key, oid))
        # add BYE team
        name = "BYE"
        nullPlayer = s.execute("SELECT id FROM people WHERE name = ?", ("Null",)).fetchone()[0]
        s.execute("INSERT INTO teams (name, captain) VALUES (?, ?)", (name, nullPlayer))
        for team in get_all_teams():
                # id INTEGER PRIMARY KEY AUTOINCREMENT,
                # name TEXT,
                # imageURL TEXT,
                # primaryColour INTEGER,
                # secondaryColour INTEGER,
                # imageURL TEXT,
                
                # captain INTEGER,
                # nonCaptain INTEGER,
                # substitute INTEGER,
            name = team.name
            imageURL = team.image_path
            primaryColor = team.primary_color
            secondaryColor = team.secondary_color
            
            captain = s.execute("SELECT id FROM people WHERE name = ?", (team.captain.name,)).fetchone()[0]
            s.execute("INSERT INTO teams (name, imageURL, primaryColor, secondaryColor, captain) VALUES (?, ?, ?, ?, ?)", (name, imageURL, primaryColor, secondaryColor, captain))
            if team.non_captain.name != "Null":
                
                # get the most recent team
                team_id = s.execute("SELECT id FROM teams ORDER BY id DESC LIMIT 1").fetchone()[0] # get the most recent team
                nonCaptain = s.execute("SELECT id FROM people WHERE name = ?", (team.non_captain.name,)).fetchone()[0]
                s.execute("UPDATE teams SET nonCaptain = ? WHERE id = ?", (nonCaptain, team_id))
            
            if len(team.players) > 2 and team.players[2].name != "Null":
                substitute = s.execute("SELECT id FROM people WHERE name = ?", (team.players[2].name,)).fetchone()[0]
                s.execute("UPDATE teams SET substitute = ? WHERE id = ?", (substitute, team_id))
        
        for tournament in comp.values():
                    # create_tournaments_table = """CREATE TABLE IF NOT EXISTS tournaments (
                    #     id INTEGER PRIMARY KEY AUTOINCREMENT,
                    #     finalsGenerator TEXT,
                    #     fixturesGenerator TEXT,
                    #     name TEXT,
                    #     officials STRING,
                    #     ranked INTEGER,
                    #     teams STRING,
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
            ranked = tournament.details.get("ranked", True)
            teams = 0
            for team in tournament.teams:
                s.execute("SELECT id FROM teams WHERE name = ?", (team.name,))
                teams += 2**s.fetchone()[0]
            officials = 0
            for official in tournament.officials:
                s.execute("SELECT id FROM people WHERE name = ?", (official.name,))
                officials += 2**s.fetchone()[0]
            # print(teams, officials)
            teams = str(teams)
            officials = str(officials)
            # print(teams, officials)
            notes = tournament.notes
        
            
            twoCourts = tournament.two_courts
            s.execute(
                "INSERT INTO tournaments (finalsGenerator, fixturesGenerator, name, officials, ranked, teams, twoCourts, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                (finalsGenerator, fixturesGenerator, name, officials, ranked, teams, twoCourts, notes)
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
            # servingScore INTEGER,
            # receivingScore INTEGER,
            # gameString TEXT,
            # started INTEGER,
            # startTime INTEGER,
            # length INTEGER,
            # court INTEGER,
            # protested INTEGER,
            # resolved INTEGER,
            # isFinal INTEGER,
            # notes TEXT,

            for round, roundgames in enumerate(tournament.fixtures):
                round += 1
                for game in roundgames:
                    process_game(tournamentId, game, round, False)
            for round, roundgames in enumerate(tournament.finals):
                round += 1
                for game in roundgames:
                    process_game(tournamentId, game, round, True)
                    
                    
                    
                
        
