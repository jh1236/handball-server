from utils.databaseManager import DatabaseManager

class Tournament:
    def __init__(self, id):
        self.id = id
        self.name 
        with DatabaseManager() as db:
            db.execute("SELECT * FROM tournaments WHERE id = %s", (id,))
            self.tournament = db.fetchone()
        