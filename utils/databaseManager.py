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
    inFinals INTEGER,
    hasScorer INTEGER,
    isPooled INTEGER,
    notes TEXT,
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
create_games_table = """CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournamentId INTEGER,
    teamOne INTEGER,
    teamTwo INTEGER,
    teamOneScore INTEGER,
    teamTwoScore INTEGER,
    teamOneTimeouts INTEGER,
    teamTwoTimeouts INTEGER,
    winningTeam INTEGER,
    started INTEGER,
    ended INTEGER,
    someoneHasWon INTEGER,
    protested INTEGER,
    resolved INTEGER,
    isRanked INTEGER,
    bestPlayer INTEGER,
    official INTEGER,
    scorer INTEGER,
    IGASide INTEGER,
    gameStringVersion INTEGER,
    gameString TEXT,
    playerToServe INTEGER,
    teamToServe INTEGER,
    sideToServe TEXT,
    startTime INTEGER,
    length INTEGER,
    court INTEGER,
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
    FOREIGN KEY (playerToServe) REFERENCES people (id),
    FOREIGN KEY (teamToServe) REFERENCES teams (id),
    FOREIGN KEY (official) REFERENCES officials (id),
    FOREIGN KEY (scorer) REFERENCES officials (id),
    FOREIGN KEY (IGASide) REFERENCES teams (id)
);"""

create_live_games_view = """CREATE VIEW IF NOT EXISTS liveGames AS
SELECT
    games.id,
    SUM(IIF(gE.teamId = games.teamOne and gE.eventType = 'Score', 1, 0)) as teamOneScore,
    SUM(IIF(gE.teamId = games.teamTwo and gE.eventType = 'Score', 1, 0)) as teamTwoScore,
    SUM(IIF(gE.teamId = games.teamOne and gE.eventType = 'Timeout', 1, 0)) as teamOneTimeouts,
    SUM(IIF(gE.teamId = games.teamTwo and gE.eventType = 'Timeout', 1, 0)) as teamTwoTimeouts,
    lastGe.nextPlayerToServe as playerToServe,
    lastGe.nextTeamToServe as teamToServe,
    lastGe.nextServeSide as sideToServe,
    (ABS(SUM(gE.teamId = games.teamOne and (gE.eventType = 'Score')) -
            SUM(gE.teamId = games.teamTwo and (gE.eventType = 'Score'))) >= 2 AND
        max(SUM(gE.teamId = games.teamOne and (gE.eventType = 'Score')),
            SUM(gE.teamId = games.teamTwo and (gE.eventType = 'Score'))) >= 11) or
       SUM(gE.eventType = 'Forfeit') > 0 as someoneHasWon,
       IIf(SUM(gE.eventType = 'Forfeit') > 0, games.teamOne + teamTwo - SUM((gE.eventType = 'Forfeit') * gE.teamId),
           iif(SUM(gE.teamId = games.teamOne and (gE.eventType = 'Score')) >
               SUM(gE.teamId = games.teamTwo and (gE.eventType = 'Score')), teamOne, teamTwo)) as winningTeam,
    SUM(IIF(gE.eventType = 'Start', 1, 0)) > 0 as started,
    SUM(IIF(gE.eventType = 'End Game', 1, 0)) > 0 as ended, --THIS NEEDS RENAMING (LACH)
    SUM(IIF(gE.eventType = 'Protest', gE.details, 0)) > 0 as protested,
    SUM(IIF(gE.eventType = 'Resolve', gE.details, 0)) > 0 as resolved
    
from games
         LEFT JOIN gameEvents gE on games.id = gE.gameId
         LEFT JOIN gameEvents lastGe on lastGe.id = (SELECT MAX(id) from gameEvents where gameEvents.gameId = games.id)
group by games.id;"""

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
create_player_game_stats_table = """CREATE TABLE IF NOT EXISTS playerGameStats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gameId INTEGER,
    playerId INTEGER,
    teamId INTEGER,
    opponentId INTEGER,
    tournamentId INTEGER,
    roundsPlayed INTEGER,
    roundsBenched INTEGER,
    isBestPlayer INTEGER,
    isFinal INTEGER,
    points INTEGER,
    aces INTEGER,
    faults INTEGER,
    servedPoints INTEGER,
    servedPointsWon INTEGER,
    servesReceived INTEGER,
    servesReturned INTEGER,
    doubleFaults INTEGER,
    greenCards INTEGER,
    warnings INTEGER,
    yellowCards INTEGER,
    redCards INTEGER,
    cardTimeRemaining INTEGER,
    cardTime INTEGER,
    startSide TEXT,
    FOREIGN KEY (gameId) REFERENCES games (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (teamId) REFERENCES teams (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (opponentID) REFERENCES teams (id)
);"""
create_player_game_stats_view = """CREATE VIEW IF NOT EXISTS livePlayerGameStats AS
SELECT playerGameStats.id,
       playerGameStats.playerId,
       coalesce(SUM(ge.eventType = 'Score' and ge.playerId = playerGameStats.playerId), 0) as points,
       coalesce(SUM(ge.eventType = 'Ace' and ge.playerId = playerGameStats.playerId), 0)   as aces,
       coalesce(SUM(ge.eventType = 'Fault' and ge.playerId = playerGameStats.playerId),
                0)                                                                         as faults,
       coalesce(SUM(gE.gameId = playerGameStats.gameId AND gE.nextPlayerToServe = playerGameStats.playerId),
                0)                                                                         as servedPoints,
       coalesce(SUM(gE.playerWhoServed = playerGameStats.playerId
           AND playerGameStats.teamId = gE.teamId
           AND gE.eventType = 'Score'),
                0)                                                                         as servedPointsWon,
       coalesce(SUM(gE.teamWhoServed <> playerGameStats.teamId
           AND ((gE.sideServed = 'Left') =
                (teamOneLeft = playerGameStats.playerId OR teamTwoRight = playerGameStats.playerId
                    AND (teamOneLeft = playerGameStats.playerId OR teamOneRight = playerGameStats.playerId OR
                         teamTwoLeft = playerGameStats.playerId OR teamTwoRight = playerGameStats.playerId)))
           and gE.eventType == 'Score'),
                0)                                                                         as servesReceived,
       coalesce(SUM(gE.teamWhoServed <> playerGameStats.teamId
           AND ((gE.sideServed = 'Left') =
                (teamOneLeft = playerGameStats.playerId OR teamTwoRight = playerGameStats.playerId
                    AND (teamOneLeft = playerGameStats.playerId OR teamOneRight = playerGameStats.playerId OR
                         teamTwoLeft = playerGameStats.playerId OR teamTwoRight = playerGameStats.playerId)))
           and gE.eventType == 'Score'),
                0) - coalesce(SUM(gE.teamWhoServed <> playerGameStats.teamId
           AND ((gE.sideServed = 'Left') =
                (teamOneLeft = playerGameStats.playerId OR teamTwoRight = playerGameStats.playerId
                    AND (teamOneLeft = playerGameStats.playerId OR teamOneRight = playerGameStats.playerId OR
                         teamTwoLeft = playerGameStats.playerId OR teamTwoRight = playerGameStats.playerId)))
           and gE.eventType == 'Ace'),
                              0)                                                           as servesReturned,
       coalesce(SUM(gE.playerWhoServed = playerGameStats.playerId
           AND gE.eventType = 'Fault' AND gE.nextPlayerToServe <> playerGameStats.playerId),
                0)                                                                         as doubleFaults, --TODO: probably broken
       coalesce(SUM(gE.playerId = playerGameStats.playerId
           AND gE.eventType = 'Green Card'),
                0)                                                                         as greenCards,
       coalesce(SUM(gE.playerId = playerGameStats.playerId
           AND gE.eventType = 'Warning'),
                0)                                                                         as warnings,
       coalesce(SUM(gE.playerId = playerGameStats.playerId
           AND gE.eventType = 'Yellow Card'),
                0)                                                                         as yellowCards,
       coalesce(SUM(gE.playerId = playerGameStats.playerId
           AND gE.eventType = 'Red Card'),
                0)                                                                         as redCards,
       IIF(
                   MIN(IIF(gE.eventType = 'Red Card' and gE.playerId = playerGameStats.playerId, -1, 0)) = -1, -1,
                   max(
                           IIF(gE.eventType LIKE '% Card' and gE.playerId = playerGameStats.playerId,
                               details - (SELECT COUNT(id)
                                          FROM gameEvents
                                          WHERE gameEvents.gameId = playerGameStats.gameId
                                            AND gameEvents.id > gE.id
                                            AND gameEvents.eventType = 'Score'),
                               0)
                   )
       )                                                                                   as cardTimeRemaining,
       IIF(
                   MIN(IIF(gE.eventType = 'Red Card' and gE.playerId = playerGameStats.playerId, -1, 0)) = -1, -1,
                   (SELECT details
                    FROM gameEvents
                    WHERE gameEvents.gameId = playerGameStats.gameId
                      AND gameEvents.playerId = playerGameStats.playerId
                      AND gameEvents.eventType LIKE '% Card'
                    ORDER BY id desc
                    LIMIT 1)
       )                                                                                   as cardTime

FROM playerGameStats
         INNER JOIN games ON playerGameStats.gameId = games.id
         LEFT JOIN gameEvents gE
                   on playerGameStats.gameId = gE.gameId
group by playerGameStats.id;
"""
create_elo_change_table = """CREATE TABLE IF NOT EXISTS eloChange (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gameId INTEGER,
    playerId INTEGER,
    tournamentId INTEGER,
    eloChange INTEGER,
    FOREIGN KEY (gameId) REFERENCES games (id),
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
    teamOneLeft INTEGER,
    teamOneRight INTEGER,
    teamTwoLeft INTEGER,
    teamTwoRight INTEGER,
    FOREIGN KEY (gameId) REFERENCES games (id),
    FOREIGN KEY (teamId) REFERENCES teams (id),
    FOREIGN KEY (nextPlayerToServe) REFERENCES people (id),
    FOREIGN KEY (nextTeamToServe) REFERENCES teams (id),
    FOREIGN KEY (playerWhoServed) REFERENCES people (id),
    FOREIGN KEY (teamOneLeft) REFERENCES people (id),
    FOREIGN KEY (teamOneRight) REFERENCES people (id),
    FOREIGN KEY (teamTwoLeft) REFERENCES people (id),
    FOREIGN KEY (teamTwoRight) REFERENCES people (id),
    FOREIGN KEY (teamWhoServed) REFERENCES teams (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id)
);"""

create_insert_game_event_trigger = """CREATE TRIGGER IF NOT EXISTS updateGames
    AFTER INSERT
    ON gameEvents
BEGIN
    UPDATE games
SET teamOneScore    = lg.teamOneScore,
    teamTwoScore    = lg.teamTwoScore,
    teamOneTimeouts = lg.teamOneTimeouts,
    teamTwoTimeouts = lg.teamTwoTimeouts,
    winningTeam     = lg.winningTeam,
    started         = lg.started,
    ended           = lg.ended,
    protested       = lg.protested,
    resolved        = lg.resolved,
    playerToServe = lg.playerToServe,
    teamToServe = lg.teamToServe,
    sideToServe = lg.sideToServe,
    someoneHasWon = lg.someoneHasWon
FROM liveGames lg
WHERE lg.id = games.id AND games.id = NEW.gameId;

    UPDATE playerGameStats
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
        AND playerGameStats.gameId = NEW.gameId;

END;
"""

create_delete_game_event_trigger = """CREATE TRIGGER IF NOT EXISTS updateGamesAgain
    AFTER DELETE
    ON gameEvents
BEGIN
    UPDATE games
SET teamOneScore    = lg.teamOneScore,
    teamTwoScore    = lg.teamTwoScore,
    teamOneTimeouts = lg.teamOneTimeouts,
    teamTwoTimeouts = lg.teamTwoTimeouts,
    winningTeam     = lg.winningTeam,
    started         = lg.started,
    ended           = lg.ended,
    protested       = lg.protested,
    resolved        = lg.resolved,
    playerToServe = lg.playerToServe,
    teamToServe = lg.teamToServe,
    sideToServe = lg.sideToServe,
    someoneHasWon = lg.someoneHasWon
FROM liveGames lg
WHERE lg.id = games.id AND games.id = OLD.gameId;

    UPDATE playerGameStats
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
        AND playerGameStats.gameId = OLD.gameId;

END;
"""


class DatabaseManager:
    def __init__(self, force_create_tables=False):
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
        if force_create_tables:
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
        self.read_write_c.execute(create_insert_game_event_trigger)
        self.read_write_c.execute(create_delete_game_event_trigger)
        self.conn.commit()

    def close_connection(self):
        if self.closed:
            return
        self.closed = True
        self.conn.commit()

        self.read_only_c.close()
        self.read_write_c.close()

        self.conn.close()

    def __enter__(self, read_only=False):
        return self.read_only_c if read_only else self.read_write_c

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    def __del__(self):
        self.close_connection()


if __name__ == "__main__":
    DatabaseManager()
