import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import ConsumptionEntry, TasteProfile


class Database:
    """SQLite database for taste profile and consumption log."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_dir = Path.home() / ".pod-discover"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "pod_discover.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS taste_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    profile_json TEXT NOT NULL DEFAULT '{}'
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consumption_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
                    notes TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS favorite_feeds (
                    feed_id INTEGER PRIMARY KEY,
                    feed_title TEXT NOT NULL,
                    added_at TEXT DEFAULT (datetime('now'))
                )
            """
            )
            conn.commit()

            # Ensure taste_profile has a default row
            cursor = conn.execute("SELECT COUNT(*) FROM taste_profile WHERE id = 1")
            if cursor.fetchone()[0] == 0:
                conn.execute("INSERT INTO taste_profile (id, profile_json) VALUES (1, '{}')")
                conn.commit()
        finally:
            conn.close()

    def get_taste_profile(self) -> TasteProfile:
        """Retrieve the current taste profile."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT profile_json FROM taste_profile WHERE id = 1")
            row = cursor.fetchone()
            if row:
                profile_data = json.loads(row[0])
                return TasteProfile(**profile_data)
            return TasteProfile()
        finally:
            conn.close()

    def update_taste_profile(self, profile: TasteProfile):
        """Update the taste profile."""
        conn = sqlite3.connect(self.db_path)
        try:
            profile_json = profile.model_dump_json()
            conn.execute("UPDATE taste_profile SET profile_json = ? WHERE id = 1", (profile_json,))
            conn.commit()
        finally:
            conn.close()

    def log_consumption(self, entry: ConsumptionEntry) -> int:
        """Log a consumption entry and return its ID."""
        conn = sqlite3.connect(self.db_path)
        try:
            timestamp = entry.timestamp or datetime.now().isoformat()
            cursor = conn.execute(
                """
                INSERT INTO consumption_log (item_type, item_id, title, rating, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (entry.item_type, entry.item_id, entry.title, entry.rating, entry.notes, timestamp),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def get_consumption_history(self, limit: int = 20) -> list[ConsumptionEntry]:
        """Retrieve recent consumption history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                """
                SELECT id, item_type, item_id, title, rating, notes, created_at as timestamp
                FROM consumption_log
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [ConsumptionEntry(**dict(row)) for row in rows]
        finally:
            conn.close()

    def add_favorite_feed(self, feed_id: int, feed_title: str):
        """Add a podcast to favorites."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO favorite_feeds (feed_id, feed_title) VALUES (?, ?)",
                (feed_id, feed_title),
            )
            conn.commit()
        finally:
            conn.close()

    def remove_favorite_feed(self, feed_id: int):
        """Remove a podcast from favorites."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM favorite_feeds WHERE feed_id = ?", (feed_id,))
            conn.commit()
        finally:
            conn.close()

    def get_favorite_feeds(self) -> list[dict]:
        """Get all favorite podcasts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT feed_id, feed_title, added_at FROM favorite_feeds ORDER BY added_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def is_favorite_feed(self, feed_id: int) -> bool:
        """Check if a feed is favorited."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT 1 FROM favorite_feeds WHERE feed_id = ?", (feed_id,)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()
