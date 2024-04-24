from utils.databaseManager import DatabaseManager



class Tournaments:
    def __init__(self):
        with DatabaseManager() as db:
            db.execute("SELECT * FROM tournaments")
            self.tournaments = db.fetchall()
    

    def make_new(self, name, fixtures_generator, finals_generator, ranked, two_courts):
        with DatabaseManager() as db:
            db.execute("INSERT INTO tournaments (name, fixturesGenerator, finalsGenerator, ranked, twoCourts) VALUES (%s, %s, %s, %s, %s)", (name, fixtures_generator, finals_generator, ranked, two_courts))
            db.execute("SELECT * FROM tournaments WHERE name = %s", (name,))
            self.tournaments.append(db.fetchone())
    
    
    
    