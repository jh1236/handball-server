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
    sideOfCourt TEXT,
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
    FOREIGN KEY (gameId) REFERENCES games (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (teamId) REFERENCES teams (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id),
    FOREIGN KEY (opponentID) REFERENCES teams (id)
);"""
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
    FOREIGN KEY (gameId) REFERENCES games (id),
    FOREIGN KEY (teamId) REFERENCES teams (id),
    FOREIGN KEY (nextPlayerToServe) REFERENCES people (id),
    FOREIGN KEY (nextTeamToServe) REFERENCES teams (id),
    FOREIGN KEY (playerWhoServed) REFERENCES people (id),
    FOREIGN KEY (teamWhoServed) REFERENCES teams (id),
    FOREIGN KEY (playerId) REFERENCES people (id),
    FOREIGN KEY (tournamentId) REFERENCES tournaments (id)
);"""

create_triggers = """CREATE TRIGGER IF NOT EXISTS updateGames
    AFTER INSERT
    ON gameEvents
BEGIN
    UPDATE games
    SET teamOneScore    = SUM(IIF(gE.teamId = g1.teamOne and gE.eventType = 'Score', 1, 0)),
        teamTwoScore    = SUM(IIF(gE.teamId = g1.teamTwo and gE.eventType = 'Score', 1, 0)),
        teamOneTimeouts = SUM(IIF(gE.teamId = g1.teamOne and gE.eventType = 'Timeout', 1, 0)),
        teamTwoTimeouts = SUM(IIF(gE.teamId = g1.teamTwo and gE.eventType = 'Timeout', 1, 0)),
        started         = SUM(IIF(gE.eventType = 'Start', 1, 0)) > 0,
        ended           = SUM(IIF(gE.eventType = 'End Game', 1, 0)) > 0,
        protested       = SUM(IIF(gE.eventType = 'Protest', gE.details, 0)) > 0,
        resolved        = SUM(IIF(gE.eventType = 'Resolve', gE.details, 0)) > 0,
        playerToServe   = lastGe.nextPlayerToServe,
        teamToServe     = lastGe.nextTeamToServe,
        sideToServe     = lastGe.nextServeSide,
        winningTeam     = IIf(SUM(gE.eventType = 'Forfeit') > 0,
                              g1.teamOne + teamTwo - SUM((gE.eventType = 'Forfeit') * gE.teamId),
                              iif(SUM(gE.teamId = g1.teamOne and (gE.eventType = 'Score')) >
                                  SUM(gE.teamId = g1.teamTwo and (gE.eventType = 'Score')), teamOne, teamTwo)),
        someoneHasWon   = (ABS(SUM(gE.teamId = g1.teamOne and (gE.eventType = 'Score')) -
                               SUM(gE.teamId = g1.teamTwo and (gE.eventType = 'Score'))) >= 2 AND
                           max(SUM(gE.teamId = g1.teamOne and (gE.eventType = 'Score')),
                               SUM(gE.teamId = g1.teamTwo and (gE.eventType = 'Score'))) >= 11) or
                          SUM(gE.eventType = 'Forfeit') > 0
    FROM games g1
             LEFT JOIN gameEvents gE
                       on g1.id = gE.gameId
             LEFT JOIN gameEvents lastGe
                       on lastGe.id = (SELECT MAX(id) from gameEvents where gameEvents.gameId = g1.id)
                           AND g1.id = NEW.gameId;

    UPDATE playerGameStats
    SET points            = coalesce(SUM(ge.eventType = 'Score' and ge.playerId = p1.playerId), 0),
        aces              = coalesce(SUM(ge.eventType = 'Ace' and ge.playerId = p1.playerId), 0),
        faults            = coalesce(SUM(ge.eventType = 'Fault' and ge.playerId = p1.playerId), 0),
        servedPoints      = coalesce(
                SUM(gE.gameId = p1.gameId AND gE.nextPlayerToServe = p1.playerId), 0),
        servedPointsWon   = coalesce(SUM(gE.gameId = p1.gameId
            AND gE.playerWhoServed = p1.playerId
            AND p1.teamId = gE.teamId
            AND gE.eventType = 'Score'), 0),
        servesReceived    = coalesce(SUM(gE.gameId = p1.gameId
            and gE.teamWhoServed <> p1.teamId
            AND gE.sideServed = p1.sideOfCourt
            and gE.eventType == 'Score'), 0),
        servesReturned    = coalesce(SUM(gE.gameId = p1.gameId
            and gE.teamWhoServed <> p1.teamId
            AND gE.sideServed = p1.sideOfCourt
            and gE.eventType == 'Score') -
                                     SUM(gE.gameId = p1.gameId
                                         and gE.teamWhoServed <> p1.teamId
                                         AND gE.sideServed = p1.sideOfCourt
                                         and gE.eventType == 'Ace'), 0),
        doubleFaults      = coalesce(SUM(gE.gameId = p1.gameId
            AND gE.playerWhoServed = p1.playerId
            AND gE.eventType = 'Fault' AND
                                         (SELECT details = 'Penalty' FROM gameEvents WHERE gameEvents.id = gE.id + 1)),
                                     0),
        greenCards        = coalesce(SUM(gE.gameId = p1.gameId
            AND gE.playerId = p1.playerId
            AND gE.eventType = 'Green Card'), 0),
        warnings          = coalesce(SUM(gE.gameId = p1.gameId
            AND gE.playerId = p1.playerId
            AND gE.eventType = 'Warning'), 0),
        yellowCards       = coalesce(SUM(gE.gameId = p1.gameId
            AND gE.playerId = p1.playerId
            AND gE.eventType = 'Yellow Card'), 0),
        redCards          = coalesce(SUM(gE.gameId = p1.gameId
            AND gE.playerId = p1.playerId
            AND gE.eventType = 'Red Card'), 0),
        cardTimeRemaining = IIF(
                MIN(IIF(gE.eventType = 'Red Card' and gE.playerId = p1.playerId, -1, 0)) = -1, -1,
                max(
                        IIF(gE.eventType LIKE '% Card' and gE.playerId = p1.playerId,
                            details - (SELECT COUNT(id)
                                       FROM gameEvents
                                       WHERE gameEvents.gameId = p1.gameId
                                         AND gameEvents.id > gE.id
                                         AND gameEvents.eventType = 'Score'),
                            0)
                )
                            ),
        cardTime          = IIF(
                MIN(IIF(gE.eventType = 'Red Card' and gE.playerId = p1.playerId, -1, 0)) = -1, -1,
                (SELECT details
                 FROM gameEvents
                 WHERE gameEvents.gameId = p1.gameId
                   AND gameEvents.playerId = p1.playerId
                   AND gameEvents.eventType LIKE '% Card'
                 ORDER BY id desc
                 LIMIT 1)
                            )
    FROM playerGameStats p1
             LEFT JOIN gameEvents gE
                       on p1.gameId = gE.gameId
    WHERE p1.gameId = NEW.gameId;

END;
"""


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
        self.read_write_c.execute(create_punishments_view)
        self.read_write_c.execute(create_triggers)
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
