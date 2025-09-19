import os
import sqlite3
from dotenv import load_dotenv
from pathlib import Path

class ManageDatabase:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        load_dotenv(self.BASE_DIR / ".env")
        self.DB_PATH = os.getenv("DATABASE_PATH")
        self.DB_NAME = os.getenv("DATABASE_NAME")
        self.db_file = os.path.join(self.DB_PATH, self.DB_NAME)

    def init_db(self):
        self.execute_database("CREATE TABLE IF NOT EXISTS Auth (access TEXT,refresh TEXT);")
        self.execute_database("CREATE TABLE IF NOT EXISTS Backaddr (sub TEXT,name TEXT,tld TEXT);")


    def execute_database(self, command):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute(command)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if conn:
                conn.close()

    def get_auth(self) -> dict | None:
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT access, refresh FROM Auth LIMIT 1;")
            row = cursor.fetchone()
            if row:
                return {"access": row[0], "refresh": row[1]}
            return None
        except sqlite3.Error as e:
            print(f"Database error in get_auth: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_backaddr(self) -> dict | None:
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT sub, name, tld FROM Backaddr LIMIT 1;")
            row = cursor.fetchone()
            if row:
                return {"sub": row[0], "name": row[1], "tld": row[2]}
            return None
        except sqlite3.Error as e:
            print(f"Database error in get_backaddr: {e}")
            return None
        finally:
            if conn:
                conn.close()
