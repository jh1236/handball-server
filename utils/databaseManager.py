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
       teamId as teamId,
       g.official as officialId,
       g.id as gameId,
       g.tournamentId as tournamentId,
       REPLACE(eventType, ' Card', '') as type,
       gameEvents.notes as reason,
       case WHEN eventType = 'Green Card' THEN '#84AA63' WHEN eventType = 'Yellow Card' THEN '#C96500'  WHEN eventType = 'Red Card' THEN '#EC4A4A' ELSE '#777777' END as hex
FROM gameEvents
         INNER JOIN main.games g on gameEvents.gameId = g.id
WHERE eventType LIKE '% Card'
   or eventType = 'Warning';"""
create_games_table = """CREATE TABLE IF NOT EXISTS gamesTable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournamentId INTEGER,
    teamOne INTEGER,
    teamTwo INTEGER,
    bestPlayer INTEGER,
    official INTEGER,
    scorer INTEGER,
    IGASide INTEGER,
    gameStringVersion INTEGER,
    gameString TEXT,
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
    FOREIGN KEY (teamOne) REFERENCES teams (id),
    FOREIGN KEY (teamTwo) REFERENCES teams (id),
    FOREIGN KEY (bestPlayer) REFERENCES people (id),
    FOREIGN KEY (official) REFERENCES officials (id),
    FOREIGN KEY (scorer) REFERENCES officials (id),
    FOREIGN KEY (IGASide) REFERENCES teams (id)
);"""

create_live_games_view = """CREATE VIEW IF NOT EXISTS games AS
SELECT
    gamesTable.*,
    SUM(IIF(gE.teamId = gamesTable.teamOne and gE.eventType = 'Score', 1, 0)) as teamOneScore,
    SUM(IIF(gE.teamId = gamesTable.teamTwo and gE.eventType = 'Score', 1, 0)) as teamTwoScore,
    SUM(IIF(gE.teamId = gamesTable.teamOne and gE.eventType = 'Timeout', 1, 0)) as teamOneTimeouts,
    SUM(IIF(gE.teamId = gamesTable.teamTwo and gE.eventType = 'Timeout', 1, 0)) as teamTwoTimeouts,
    lastGe.nextPlayerToServe as playerToServe,
    lastGe.nextTeamToServe as teamToServe,
    lastGe.nextServeSide as sideToServe,
    (ABS(SUM(gE.teamId = gamesTable.teamOne and (gE.eventType = 'Score')) -
            SUM(gE.teamId = gamesTable.teamTwo and (gE.eventType = 'Score'))) >= 2 AND
        max(SUM(gE.teamId = gamesTable.teamOne and (gE.eventType = 'Score')),
            SUM(gE.teamId = gamesTable.teamTwo and (gE.eventType = 'Score'))) >= 11) or
       SUM(gE.eventType = 'Forfeit') > 0 as finished,
       IIf(SUM(gE.eventType = 'Forfeit') > 0, gamesTable.teamOne + teamTwo - SUM((gE.eventType = 'Forfeit') * gE.teamId),
           iif(SUM(gE.teamId = gamesTable.teamOne and (gE.eventType = 'Score')) >
               SUM(gE.teamId = gamesTable.teamTwo and (gE.eventType = 'Score')), teamOne, teamTwo)) as winningTeam,
    SUM(IIF(gE.eventType = 'Start', 1, 0)) > 0 as started
    
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
       SUM(ge.eventType = 'Score' and ge.playerId = playerGameStatsTable.playerId) as points,
       SUM(ge.eventType = 'Ace' and ge.playerId = playerGameStatsTable.playerId)                           as aces,
       SUM(ge.eventType = 'Fault' and ge.playerId = playerGameStatsTable.playerId)                         as faults,
       SUM(gE.gameId = playerGameStatsTable.gameId AND gE.nextPlayerToServe = playerGameStatsTable.playerId)    as servedPoints,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerWhoServed = playerGameStatsTable.playerId
           AND playerGameStatsTable.teamId = gE.teamId
           AND gE.eventType = 'Score')                                          as servedPointsWon,
       SUM(gE.gameId = playerGameStatsTable.gameId
           and gE.teamWhoServed <> playerGameStatsTable.teamId
           AND gE.sideServed = playerGameStatsTable.sideOfCourt)                                           as servesReceived,
       SUM(gE.gameId = playerGameStatsTable.gameId
           and gE.teamWhoServed <> playerGameStatsTable.teamId
           AND gE.sideServed = playerGameStatsTable.sideOfCourt
           and gE.eventType == 'Score') - 
       SUM(gE.gameId = playerGameStatsTable.gameId
           and gE.teamWhoServed <> playerGameStatsTable.teamId
           AND gE.sideServed = playerGameStatsTable.sideOfCourt
           and gE.eventType == 'Ace')                                                                 as servesReturned,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerWhoServed = playerGameStatsTable.playerId
           AND gE.eventType = 'Fault' AND gE.nextPlayerToServe <> playerGameStatsTable.playerId)           as doubleFaults,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerId = playerGameStatsTable.playerId
           AND gE.eventType = 'Green Card')                                                           as greenCards,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerId = playerGameStatsTable.playerId
           AND gE.eventType = 'Warning')                                                           as warnings,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerId = playerGameStatsTable.playerId
           AND gE.eventType = 'Yellow Card')                                                          as yellowCards,
       SUM(gE.gameId = playerGameStatsTable.gameId
           AND gE.playerId = playerGameStatsTable.playerId
           AND gE.eventType = 'Red Card')                                                          as redCards,
           
       IIF(
               MIN(IIF(gE.eventType = 'Red Card' and gE.playerId = playerGameStatsTable.playerId, -1, 0)) = -1, -1,
               max(
                       IIF(gE.eventType LIKE '% Card' and gE.playerId = playerGameStatsTable.playerId,
                           details - (SELECT COUNT(id)
                                      FROM gameEvents
                                      WHERE gameEvents.gameId = playerGameStatsTable.gameId
                                        AND gameEvents.id > gE.id
                                        AND gameEvents.eventType = 'Score'),
                           0)
               )
       ) as cardTimeRemaining,
       IIF(
               MIN(IIF(gE.eventType = 'Red Card' and gE.playerId = playerGameStatsTable.playerId, -1, 0)) = -1, -1,
               (SELECT details
                FROM gameEvents
                WHERE gameEvents.gameId = playerGameStatsTable.gameId
                  AND gameEvents.playerId = playerGameStatsTable.playerId
                  AND gameEvents.eventType LIKE '% Card'
                ORDER BY id desc
                LIMIT 1)
       ) as cardTime

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