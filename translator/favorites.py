"""Local learning list, separate from the bundled read-only dictionary."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3


class FavoritesStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('''CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY, original TEXT NOT NULL UNIQUE,
                translation TEXT NOT NULL, saved_at TEXT NOT NULL)''')

    def save(self, original, translation):
        original, translation = original.strip(), translation.strip()
        if not original or not translation:
            raise ValueError('没有可收藏的翻译内容')
        now = datetime.now().astimezone().isoformat(timespec='seconds')
        with closing(sqlite3.connect(self.path)) as db, db:
            row = db.execute('SELECT translation FROM favorites WHERE original=?', (original,)).fetchone()
            if row and row[0] == translation:
                return 'exists'
            db.execute('''INSERT INTO favorites(original,translation,saved_at) VALUES(?,?,?)
                ON CONFLICT(original) DO UPDATE SET translation=excluded.translation,saved_at=excluded.saved_at''',
                (original, translation, now))
            return 'updated' if row else 'saved'

    def list(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute('SELECT * FROM favorites ORDER BY saved_at DESC,id DESC')]

    def delete(self, id_):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('DELETE FROM favorites WHERE id=?', (id_,))
