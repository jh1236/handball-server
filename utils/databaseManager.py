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
create_punishments_view = """CREATE VIEW IF NOT EXISTS punishments AS
SELECT playerId as playerId,
       g.official as officialId,
       g.id as gameId,
       REPLACE(eventType, ' Card', '') as type,
       gameEvents.notes as reason
FROM gameEvents
         INNER JOIN main.games g on gameEvents.gameId = g.id
WHERE eventType LIKE '% Card'
   or eventType = 'Warning';"""
create_games_table = """CREATE TABLE IF NOT EXISTS gamesTable (
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
    status TEXT,
    adminStatus TEXT,
    
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (servingTeam) REFERENCES teams (id),
    FOREIGN KEY (receivingTeam) REFERENCES teams (id),
    FOREIGN KEY (winningTeam) REFERENCES teams (id),
    FOREIGN KEY (bestPlayer) REFERENCES people (id),
    FOREIGN KEY (official) REFERENCES officials (id),
    FOREIGN KEY (scorer) REFERENCES officials (id),
    FOREIGN KEY (IGASide) REFERENCES teams (id)
);"""

create_live_games_view = """CREATE VIEW IF NOT EXISTS games AS
SELECT
    gamesTable.*,
    SUM(gE.teamId = gamesTable.servingTeam and (gE.eventType = 'Score' or gE.eventType = 'Ace')) as servingScore,
    SUM(gE.teamId = gamesTable.receivingTeam) as receivingScore,
    lastGe.nextPlayerToServe as playerToServe,
    lastGe.nextTeamToServe as teamToServe
from gamesTable
         LEFT JOIN gameEvents gE on gamesTable.id = gE.gameId
         LEFT JOIN gameEvents lastGe on lastGe.id = (SELECT MAX(id) from gameEvents where gameEvents.gameId = gamesTable.id)
group by gamesTable.id;"""

create_tournament_teams_table = """CREATE TABLE IF NOT EXISTS tournamentTeams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournamentId INTEGER,
    teamId INTEGER,
    gamesWon INTEGER,
    gamesPlayed INTEGER,
    gamesLost INTEGER,
    timeoutsCalled INTEGER,
    pool INTEGER,
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
create_player_game_stats_table = """CREATE TABLE IF NOT EXISTS playerGameStatsTable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gameId INTEGER,
    playerId INTEGER,
    teamId INTEGER,
    opponentId INTEGER,
    tournamentId INTEGER,
    cardTime INTEGER,
    cardTimeRemaining INTEGER,
    roundsPlayed INTEGER,
    roundsBenched INTEGER,
    isBestPlayer INTEGER,
    sideOfCourt TEXT,
    isFinal INTEGER,
    FOREIGN KEY (gameId) REFERENCES gamesTable (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (teamId) REFERENCES teams (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (opponentID) REFERENCES teams (id)
);"""
create_player_game_stats_view = """
CREATE VIEW IF NOT EXISTS playerGameStats AS SELECT playerGameStatsTable.*,
       SUM((ge.eventType = 'Ace' or ge.eventType = 'Score') * ge.playerId = playerGameStatsTable.playerId) as points,
       SUM((ge.eventType = 'Ace') * ge.playerId = playerGameStatsTable.playerId)                           as aces,
       SUM((ge.eventType = 'Fault') * ge.playerId = playerGameStatsTable.playerId)                         as faults,
       SUM(gE.gameId = playerGameStatsTable.gameId AND gE.nextPlayerToServe = playerGameStatsTable.playerId)    as servedPoints,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerWhoServed = playerGameStatsTable.playerId
           AND playerGameStatsTable.teamId = gE.teamId
           AND
           (gE.eventType = 'Score' or gE.eventType = 'Ace'))                                          as servedPointsWon,
       SUM(gE.gameId = playerGameStatsTable.gameId
           and gE.teamWhoServed <> playerGameStatsTable.teamId
           AND gE.sideServed = playerGameStatsTable.sideOfCourt)                                           as servesReceived,
       SUM(gE.gameId = playerGameStatsTable.gameId
           and gE.teamWhoServed <> playerGameStatsTable.teamId
           AND gE.sideServed = playerGameStatsTable.sideOfCourt
           and gE.eventType <> 'Ace')                                                                 as servesReturned,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerWhoServed = playerGameStatsTable.playerId
           AND gE.eventType = 'Fault' AND gE.nextPlayerToServe <> playerGameStatsTable.playerId)           as doubleFaults,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerId = playerGameStatsTable.playerId
           AND gE.eventType = 'Green Card')                                                           as greenCards,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerId = playerGameStatsTable.playerId
           AND gE.eventType = 'Yellow Card')                                                          as yellowCards,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerId = playerGameStatsTable.playerId
           AND gE.eventType = 'Red Card')                                                          as redCards
FROM playerGameStatsTable
         LEFT JOIN gameEvents gE
                   on playerGameStatsTable.gameId = gE.gameId
group by playerGameStatsTable.id;
"""
create_elo_change_table = """CREATE TABLE IF NOT EXISTS eloChange (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gameId INTEGER,
    playerId INTEGER,
    tournamentId INTEGER,
    eloChange INTEGER,
    FOREIGN KEY (gameId) REFERENCES gamesTable (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id)
);"""
create_game_event_table = """CREATE TABLE IF NOT EXISTS gameEvents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gameId INTEGER,
    teamId INTEGER,
    playerId INTEGER,
    tournamentId INTEGER,
    eventType TEXT,
    time REAL,
    details INTEGER,
    notes TEXT,
    playerWhoServed INTEGER,
    teamWhoServed INTEGER,
    sideServed TEXT,
    nextPlayerToServe INTEGER,
    nextTeamToServe INTEGER,
    nextServeSide TEXT,
    FOREIGN KEY (gameId) REFERENCES gamesTable (id),
    FOREIGN KEY (teamId) REFERENCES teams (id),
    FOREIGN KEY (nextPlayerToServe) REFERENCES people (id),
    FOREIGN KEY (nextTeamToServe) REFERENCES teams (id),
    FOREIGN KEY (playerWhoServed) REFERENCES people (id),
    FOREIGN KEY (teamWhoServed) REFERENCES teams (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id)
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
        self.read_write_c.execute(create_taunts_table)
        self.read_write_c.execute(create_tournament_teams_table)
        self.read_write_c.execute(create_tournament_officials_table)
        self.read_write_c.execute(create_player_game_stats_table)
        self.read_write_c.execute(create_elo_change_table)
        self.read_write_c.execute(create_game_event_table)
        self.read_write_c.execute(create_live_games_view)
        self.read_write_c.execute(create_punishments_view)
        self.read_write_c.execute(create_player_game_stats_view)
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
    with DatabaseManager() as c:
        c.execute("SELECT id FROM tournaments WHERE searchableName=?", (tournament_name,))
        return c.fetchone()[0]


if __name__ == "__main__":
    DatabaseManager()