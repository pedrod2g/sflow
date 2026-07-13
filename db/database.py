import sqlite3
from config import DB_PATH


class TranscriptionDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    language TEXT,
                    duration_seconds REAL,
                    model TEXT DEFAULT 'whisper-large-v3-turbo',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at
                ON transcriptions(created_at)
            """)
            # Migration: add audio_path if missing (allows retry from history)
            cols = [r[1] for r in conn.execute("PRAGMA table_info(transcriptions)").fetchall()]
            if "audio_path" not in cols:
                conn.execute("ALTER TABLE transcriptions ADD COLUMN audio_path TEXT")

    def insert(self, text: str, language: str = None, duration_seconds: float = None,
               model: str = "whisper-large-v3-turbo", audio_path: str = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO transcriptions (text, language, duration_seconds, model, audio_path) VALUES (?, ?, ?, ?, ?)",
                (text, language, duration_seconds, model, audio_path),
            )
            return cursor.lastrowid

    def update_text(self, row_id: int, new_text: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE transcriptions SET text = ? WHERE id = ?",
                (new_text, row_id),
            )

    def get_recent(self, limit: int = 20) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM transcriptions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get(self, row_id: int) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            r = conn.execute("SELECT * FROM transcriptions WHERE id = ?", (row_id,)).fetchone()
            return dict(r) if r else None

    def search(self, query: str, limit: int = 20) -> list:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM transcriptions WHERE text LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def count(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[0]

    def prune_old_audio_paths(self, days: int = 7) -> list[str]:
        """Return paths of WAVs older than `days` so caller can unlink them. Clears audio_path in DB."""
        import os
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, audio_path FROM transcriptions WHERE audio_path IS NOT NULL AND created_at < ?",
                (cutoff,),
            ).fetchall()
            paths = [r[1] for r in rows if r[1] and os.path.exists(r[1])]
            if rows:
                conn.execute(
                    "UPDATE transcriptions SET audio_path = NULL WHERE audio_path IS NOT NULL AND created_at < ?",
                    (cutoff,),
                )
        return paths
