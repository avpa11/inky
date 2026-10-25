import json
import sqlite3
from pathlib import Path


class Store:
    """Connections are short-lived; callers serialize state changes in the service."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "home.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=5)

    def get(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, **values):
        with self.connect() as db:
            db.executemany("INSERT OR REPLACE INTO state VALUES (?,?)",
                           [(key, json.dumps(value, ensure_ascii=False)) for key, value in values.items()])
