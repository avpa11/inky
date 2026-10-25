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
            db.execute("CREATE TABLE IF NOT EXISTS daily_french (day TEXT PRIMARY KEY, lesson TEXT NOT NULL)")
            db.execute('CREATE TABLE IF NOT EXISTS french_seen (word TEXT PRIMARY KEY)')
            for (payload,) in db.execute('SELECT lesson FROM daily_french'):
                lesson = json.loads(payload)
                db.execute('INSERT OR IGNORE INTO french_seen VALUES (?)',
                           (lesson.get('lexeme_id', lesson['theme'].casefold()),))

    def seen_words(self):
        with self.connect() as db:
            return {row[0] for row in db.execute('SELECT word FROM french_seen')}

    def remember(self, lesson):
        word = lesson.get('lexeme_id', lesson['theme'].casefold())
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO french_seen VALUES (?)', (word,))

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

    def daily_lesson(self, day, create):
        """Pin the selected content so a later catalog release cannot rewrite history."""
        with self.connect() as db:
            row = db.execute('SELECT lesson FROM daily_french WHERE day=?', (day,)).fetchone()
        if row:
            lesson = json.loads(row[0])
            self.remember(lesson)
            return lesson
        payload = json.dumps(create(), ensure_ascii=False)
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO daily_french VALUES (?,?)', (day, payload))
            row = db.execute('SELECT lesson FROM daily_french WHERE day=?', (day,)).fetchone()
        lesson = json.loads(row[0])
        self.remember(lesson)
        return lesson
