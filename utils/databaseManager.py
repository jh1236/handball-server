import sqlite3

create_taunts_table = """CREATE TABLE IF NOT EXISTS taunts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT,
    taunt TEXT
);"""
create_officials_table = """CREATE TABLE IF NOT EXISTS officials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personId INTEGER,
    isAdmin INTEGER,
    proficiency INTEGER,
    FOREIGN KEY (personId) REFERENCES people (id)
);"""
create_people_table = """CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    searchableName TEXT,
    password TEXT,
    imageURL TEXT,
    sessionToken TEXT,
    tokenTimeout INTEGER
);"""
create_teams_table = """CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    searchableName TEXT,
    imageURL TEXT,
    primaryColor TEXT,
    secondaryColor TEXT,
    
    captain INTEGER,
    nonCaptain INTEGER,
    substitute INTEGER,
    
    FOREIGN KEY (captain) REFERENCES people (id),
    FOREIGN KEY (nonCaptain) REFERENCES people (id),
    FOREIGN KEY (substitute) REFERENCES people (id)
);"""
create_tournaments_table = """CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    searchableName TEXT,
    fixturesGenerator TEXT,
    finalsGenerator TEXT,
    ranked INTEGER,
    twoCourts INTEGER,
    isFinished INTEGER,
    isPooled INTEGER,
    notes STRING,
    imageURL TEXT
);"""
create_punishments_table = """CREATE TABLE IF NOT EXISTS punishments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personId INTEGER,
    officialId INTEGER,
    gameId INTEGER,
    color STRING, -- TODO: change to individual references for each type of punishment
    length INTEGER,
    reason STRING,
    FOREIGN KEY (personId) REFERENCES people (id),
    FOREIGN KEY (officialId) REFERENCES officials (id),
    FOREIGN KEY (gameId) REFERENCES games (id)
    );"""
create_games_table = """CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournamentId INTEGER,
    servingTeam INTEGER,
    receivingTeam INTEGER,
    winningTeam INTEGER,
    bestPlayer INTEGER,
    official INTEGER,
    scorer INTEGER,
    IGASide INTEGER,
    gameStringVersion INTEGER,
    servingScore INTEGER,
    receivingScore INTEGER,
    gameString TEXT,
    started INTEGER,
    startTime INTEGER,
    length INTEGER,
    court INTEGER,
    protested INTEGER,
    resolved INTEGER,
    isFinal INTEGER,
    round INTEGER,
    notes TEXT,
    isBye INTEGER,
    pool INTEGER,
    
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (servingTeam) REFERENCES teams (id),
    FOREIGN KEY (receivingTeam) REFERENCES teams (id),
    FOREIGN KEY (winningTeam) REFERENCES teams (id),
    FOREIGN KEY (bestPlayer) REFERENCES people (id),
    FOREIGN KEY (official) REFERENCES officials (id),
    FOREIGN KEY (scorer) REFERENCES officials (id),
    FOREIGN KEY (IGASide) REFERENCES teams (id)
);"""
create_tournament_teams_table = """CREATE TABLE IF NOT EXISTS tournamentTeams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournamentId INTEGER,
    teamId INTEGER,
    gamesWon INTEGER,
    gamesPlayed INTEGER,
    gamesLost INTEGER,
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (teamId) REFERENCES teams (id)
);"""
create_tournament_officials_table = """CREATE TABLE IF NOT EXISTS tournamentOfficials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournamentId INTEGER,
    officialId INTEGER,
    isUmpire INTEGER,
    isScorer INTEGER,
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (officialId) REFERENCES officials (id)
);"""
create_player_game_stats_table = """CREATE TABLE IF NOT EXISTS playerGameStats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gameId INTEGER,
    playerId INTEGER,
    teamId INTEGER,
    tournamentId INTEGER,
    points INTEGER,
    aces INTEGER,
    faults INTEGER,
    servedPoints INTEGER,
    servedPointsWon INTEGER,
    servesReceived INTEGER,
    servesReturned INTEGER,
    doubleFaults INTEGER,
    greenCards INTEGER,
    yellowCards INTEGER,
    redCards INTEGER,
    cardTime INTEGER,
    cardTimeRemaining INTEGER,
    roundsPlayed INTEGER,
    roundsBenched INTEGER,
    isBestPlayer INTEGER,
    isFinal INTEGER,
    FOREIGN KEY (gameId) REFERENCES games (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (teamId) REFERENCES teams (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id)
);"""
create_elo_change_table = """CREATE TABLE IF NOT EXISTS eloChange (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gameId INTEGER,
    playerId INTEGER,
    eloChange INTEGER,
    FOREIGN KEY (gameId) REFERENCES games (id),
    FOREIGN KEY (playerId) REFERENCES people (id)
);"""

class DatabaseManager:
    def __init__(self):
        self.closed = False
        self.conn = sqlite3.connect("./resources/database.db")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()
        # Create a cursor with read-only permission
        self.read_only_c = self.conn.cursor()
        self.read_only_c.execute("PRAGMA query_only = ON")

        # Create a cursor with read-write permission
        self.read_write_c = self.conn.cursor()
        self.read_write_c.execute("PRAGMA query_only = OFF")
        
        self.create_tables()

    def create_tables(self):
        self.read_write_c.execute(create_tournaments_table)
        self.read_write_c.execute(create_people_table)
        self.read_write_c.execute(create_officials_table)
        self.read_write_c.execute(create_teams_table)
        self.read_write_c.execute(create_games_table)
        self.read_write_c.execute(create_punishments_table)
        self.read_write_c.execute(create_taunts_table)
        self.read_write_c.execute(create_tournament_teams_table)
        self.read_write_c.execute(create_tournament_officials_table)
        self.read_write_c.execute(create_player_game_stats_table)
        self.read_write_c.execute(create_elo_change_table)
        self.conn.commit()

    def close_connection(self):
        if self.closed:
            return
        self.closed = True
        self.conn.commit()
        
        self.read_only_c.close()
        self.read_write_c.close()
        
        self.conn.close()
    
    def get_all_tournaments(self):
        self.read_only_c.execute("SELECT * FROM tournaments")
        return self.c.fetchall()
    
    def get_all_games_from_tournament(self, tournament_id):
        self.read_only_c.execute("SELECT * FROM games WHERE tournament_id=?", (tournament_id,))
        return self.c.fetchall()
        
    def __enter__(self, read_only=False):
        return self.read_only_c if read_only else self.read_write_c
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()
        
    def __del__(self):
        self.close_connection()


def get_tournament_id(tournament_name):
    print(tournament_name)
    with DatabaseManager() as c:
        c.execute("SELECT id FROM tournaments WHERE searchableName=?", (tournament_name,))
        return c.fetchone()[0]


if __name__ == "__main__":
    DatabaseManager()