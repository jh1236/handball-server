import sqlite3

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
    password TEXT,
    imageURL TEXT,
    sessionToken TEXT,
    tokenTimeout INTEGER
);"""


create_teams_table = """CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
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
    fixturesGenerator TEXT,
    finalsGenerator TEXT,
    officials STRING,
    teams STRING,
    ranked INTEGER,
    twoCourts INTEGER,
    notes STRING,
    logoURL STRING
);"""

# officials and teams is stored as sum(2**[officials/teams](id)) for each official/team in the tournament
# to get official or team for a tournament, do a bitwise AND with 2**[officials/teams](id) and tournaments([officials/teams])

# kept as string because of int size limitations
# will have a parse function so this is never revealed but here is the reasoning if someone ever looks at this
# in the backend for whatever reason
create_punishments_table = """CREATE TABLE IF NOT EXISTS punishments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    personId INTEGER,
    officialId INTEGER,
    gameId INTEGER,
    color STRING,
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
    
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (servingTeam) REFERENCES teams (id),
    FOREIGN KEY (receivingTeam) REFERENCES teams (id),
    FOREIGN KEY (bestPlayer) REFERENCES people (id),
    FOREIGN KEY (official) REFERENCES officials (id),
    FOREIGN KEY (scorer) REFERENCES officials (id),
    FOREIGN KEY (IGASide) REFERENCES teams (id)
);"""
#

class DatabaseManager:
    def __init__(self):
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
        self.closed = False

    def create_tables(self):
        self.read_write_c.execute(create_tournaments_table)
        self.read_write_c.execute(create_people_table)
        self.read_write_c.execute(create_officials_table)
        self.read_write_c.execute(create_teams_table)
        self.read_write_c.execute(create_games_table)
        self.read_write_c.execute(create_punishments_table)
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
