import sqlite3

create_punishments_view = """CREATE VIEW IF NOT EXISTS punishments AS
SELECT player_id as player_id,
       team_id as team_id,
       g.official_id as official_id,
       g.id as game_id,
       g.tournament_id as tournament_id,
       REPLACE(event_type, ' Card', '') as type,
       gameEvents.notes as reason,
       case WHEN event_type = 'Green Card' THEN '#84AA63' WHEN event_type = 'Yellow Card' THEN '#C96500'  WHEN event_type = 'Red Card' THEN '#EC4A4A' ELSE '#777777' END as hex
FROM gameEvents
         INNER JOIN main.games g on gameEvents.game_id = g.id
WHERE event_type LIKE '% Card'
   or event_type = 'Warning';"""

class DatabaseManager:
    def __init__(self, force_create_tables=False, path=None):
        self.closed = False
        self.path = path or "./instance/database.db"
        self.conn = sqlite3.connect("./instance/database.db")
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
        # everything but the punishments view is created via the ORM
        self.read_write_c.execute(create_punishments_view)
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
