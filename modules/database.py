import sqlite3
from modules import path_helpers
from configuration import CONFIG

class ManageDatabase:
    def __init__(self):

        self.DB_NAME = CONFIG["DATABASE_NAME"]
        self.DOMAIN_SUB = CONFIG["DOMAIN_SUB"]
        self.DOMAIN_NAME = CONFIG["DOMAIN_NAME"]
        self.DOMAIN_TLD = CONFIG["DOMAIN_TLD"]
        self.DOMAIN_IP = CONFIG["DOMAIN_IP"]
        self.DOMAIN_PORT = CONFIG["DOMAIN_PORT"]

        self.db_file = str(path_helpers.get_database_path(self.DB_NAME))
        self.default_theme = "dark"

    def init_db(self):
        self.execute_database("CREATE TABLE IF NOT EXISTS Auth (access TEXT,refresh TEXT);")
        self.execute_database("CREATE TABLE IF NOT EXISTS Backaddr (sub TEXT,name TEXT,tld TEXT,port INTEGER, ip TEXT);")
        self.execute_database("CREATE TABLE IF NOT EXISTS Settings (key TEXT PRIMARY KEY, value TEXT);")
        self.execute_database("CREATE TABLE IF NOT EXISTS Exclusives (address TEXT);")

        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Backaddr;")
                cursor.execute(
                    "INSERT INTO Backaddr (sub, name, tld, port, ip) VALUES (?, ?, ?, ?, ?);",
                    (self.DOMAIN_SUB, self.DOMAIN_NAME, self.DOMAIN_TLD, self.DOMAIN_PORT, self.DOMAIN_IP)
                )
                cursor.execute("SELECT value FROM Settings WHERE key = ? LIMIT 1;", ("theme",))
                row = cursor.fetchone()
                if not row or not row[0] or str(row[0]).strip().lower() == "none":
                    cursor.execute(
                        "INSERT OR REPLACE INTO Settings (key, value) VALUES (?, ?);",
                        ("theme", self.default_theme)
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
                try:
                    cursor.execute("SELECT ip FROM Backaddr LIMIT 1;")
                    ip_row = cursor.fetchone()
                    ip_val = ip_row[0] if ip_row and ip_row[0] is not None else ""
                except Exception:
                    ip_val = ""
                return {"sub": row[0], "name": row[1], "tld": row[2], "port": row[3], "ip": ip_val}
            return None
        except sqlite3.Error as e:
            print(f"Database error in get_backaddr: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_exclusive_addresses(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT address FROM Exclusives;")
            rows = cursor.fetchall()
            if rows:
                return [row[0] for row in rows]
            return None
        except sqlite3.Error as e:
            print(f"Database error in get_exclusives: {e}")
            return None
        finally:
            if conn:
                conn.close()
            
    def set_exclusive_addresses(self, address_list):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Exclusives;")
            cursor.executemany(
                "INSERT INTO Exclusives (address) VALUES (?);",
                [(addr,) for addr in address_list]
            )
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error in set_exclusive_addresses: {e}")
        finally:
            if conn:
                conn.close()

    def set_setting(self, key: str, value: str):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO Settings (key, value) VALUES (?, ?);", (key, value))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error in set_setting: {e}")
        finally:
            if conn:
                conn.close()

    def get_setting(self, key: str):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM Settings WHERE key = ? LIMIT 1;", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return None
        except sqlite3.Error as e:
            print(f"Database error in get_setting: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def set_theme(self, theme_name: str):
        value = (theme_name or "").strip().lower()
        if not value or value == "none":
            value = self.default_theme
        return self.set_setting("theme", value)

    def get_theme(self):
        value = self.get_setting("theme")
        if not value:
            return self.default_theme
        value = str(value).strip().lower()
        if value in {"dark", "light", "blue"}:
            return value
        return self.default_theme
