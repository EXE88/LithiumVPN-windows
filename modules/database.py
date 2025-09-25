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
        self.DOMAIN_SUB = os.getenv("DOMAIN_SUB")
        self.DOMAIN_NAME = os.getenv("DOMAIN_NAME")
        self.DOMAIN_TLD = os.getenv("DOMAIN_TLD")
        self.DOMAIN_PORT = os.getenv("DOMAIN_PORT")

        self.db_file = os.path.join(self.DB_PATH, self.DB_NAME)

    def init_db(self):
        self.execute_database("CREATE TABLE IF NOT EXISTS Auth (access TEXT,refresh TEXT);")
        self.execute_database("CREATE TABLE IF NOT EXISTS Backaddr (sub TEXT,name TEXT,tld TEXT,port INTEGER);")
        self.execute_database("CREATE TABLE IF NOT EXISTS Config (config_id TEXT,config_code TEXT,gb_eft BIGINT,days_left BIGINT);")

        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Backaddr;")
                cursor.execute(
                    "INSERT INTO Backaddr (sub, name, tld, port) VALUES (?, ?, ?, ?);",
                    (self.DOMAIN_SUB, self.DOMAIN_NAME, self.DOMAIN_TLD, self.DOMAIN_PORT)
                )
                conn.commit()
        except sqlite3.Error as e:
            print(f"Database error in init_db (Backaddr insert): {e}")


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

    def save_tokens_first_time(self, access, refresh):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO Auth(access, refresh) VALUES(?, ?);", (access, refresh))
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
            cursor.execute("SELECT sub, name, tld, port FROM Backaddr LIMIT 1;")
            row = cursor.fetchone()
            if row:
                return {"sub": row[0], "name": row[1], "tld": row[2], "port":row[3]}
            return None
        except sqlite3.Error as e:
            print(f"Database error in get_backaddr: {e}")
            return None
        finally:
            if conn:
                conn.close()
