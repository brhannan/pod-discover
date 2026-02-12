import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import ConsumptionEntry, QueueEntry, TasteProfile


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
        self.conn = sqlite3.connect(self.db_path)

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS taste_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                profile_json TEXT NOT NULL DEFAULT '{}'
            )
        """
        )
        self.conn.execute(
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
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS favorite_feeds (
                feed_id INTEGER PRIMARY KEY,
                feed_title TEXT NOT NULL,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendations_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_hash TEXT NOT NULL,
                user_request TEXT DEFAULT '',
                response_json TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(profile_hash, user_request)
            )
        """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS my_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER NOT NULL UNIQUE,
                episode_title TEXT NOT NULL,
                feed_id INTEGER,
                feed_title TEXT,
                image TEXT,
                url TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """
        )
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trending_cache (
                cache_type TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS reddit_mentions (
                podcast_name TEXT PRIMARY KEY,
                mention_count INTEGER DEFAULT 1,
                subreddits TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

        # Ensure taste_profile has a default row
        cursor = self.conn.execute("SELECT COUNT(*) FROM taste_profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            self.conn.execute("INSERT INTO taste_profile (id, profile_json) VALUES (1, '{}')")
            self.conn.commit()

    def get_taste_profile(self) -> TasteProfile:
        """Retrieve the current taste profile."""
        cursor = self.conn.execute("SELECT profile_json FROM taste_profile WHERE id = 1")
        row = cursor.fetchone()
        if row:
            profile_data = json.loads(row[0])
            return TasteProfile(**profile_data)
        return TasteProfile()

    def update_taste_profile(self, profile: TasteProfile):
        """Update the taste profile."""
        profile_json = profile.model_dump_json()
        self.conn.execute("UPDATE taste_profile SET profile_json = ? WHERE id = 1", (profile_json,))
        self.conn.commit()

    def log_consumption(self, entry: ConsumptionEntry) -> int:
        """Log a consumption entry and return its ID."""
        timestamp = entry.timestamp or datetime.now().isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO consumption_log (item_type, item_id, title, rating, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (entry.item_type, entry.item_id, entry.title, entry.rating, entry.notes, timestamp),
        )
        self.conn.commit()
        return cursor.lastrowid or 0

    def get_consumption_history(self, limit: int = 20) -> list[ConsumptionEntry]:
        """Retrieve recent consumption history."""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.execute(
            """
            SELECT id, item_type, item_id, title, rating, notes, created_at as timestamp
            FROM consumption_log
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (limit,),
        )
        rows = cursor.fetchall()
        self.conn.row_factory = None
        return [ConsumptionEntry(**dict(row)) for row in rows]

    def add_favorite_feed(self, feed_id: int, feed_title: str):
        """Add a podcast to favorites."""
        self.conn.execute(
            "INSERT OR REPLACE INTO favorite_feeds (feed_id, feed_title) VALUES (?, ?)",
            (feed_id, feed_title),
        )
        self.conn.commit()

    def remove_favorite_feed(self, feed_id: int):
        """Remove a podcast from favorites."""
        self.conn.execute("DELETE FROM favorite_feeds WHERE feed_id = ?", (feed_id,))
        self.conn.commit()

    def get_favorite_feeds(self) -> list[dict]:
        """Get all favorite podcasts."""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.execute(
            "SELECT feed_id, feed_title, added_at FROM favorite_feeds ORDER BY added_at DESC"
        )
        result = [dict(row) for row in cursor.fetchall()]
        self.conn.row_factory = None
        return result

    def is_favorite_feed(self, feed_id: int) -> bool:
        """Check if a feed is favorited."""
        cursor = self.conn.execute(
            "SELECT 1 FROM favorite_feeds WHERE feed_id = ?", (feed_id,)
        )
        return cursor.fetchone() is not None

    # --- Recommendations Cache ---

    def get_cached_recommendations(
        self, profile_hash: str, user_request: str, max_age_minutes: int = 60
    ) -> str | None:
        """Return cached JSON or None if expired/missing."""
        cursor = self.conn.execute(
            """
            SELECT response_json FROM recommendations_cache
            WHERE profile_hash = ? AND user_request = ?
              AND datetime(created_at, '+' || ? || ' minutes') > datetime('now')
            """,
            (profile_hash, user_request, max_age_minutes),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def set_cached_recommendations(
        self, profile_hash: str, user_request: str, response_json: str
    ):
        """Upsert a cache entry."""
        self.conn.execute(
            """
            INSERT INTO recommendations_cache (profile_hash, user_request, response_json)
            VALUES (?, ?, ?)
            ON CONFLICT(profile_hash, user_request)
            DO UPDATE SET response_json = excluded.response_json,
                         created_at = datetime('now')
            """,
            (profile_hash, user_request, response_json),
        )
        self.conn.commit()

    # --- My List ---

    def get_my_list(self) -> list[QueueEntry]:
        """Return all queue entries ordered by added_at DESC."""
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.execute(
            "SELECT * FROM my_list ORDER BY added_at DESC"
        )
        result = [QueueEntry(**dict(row)) for row in cursor.fetchall()]
        self.conn.row_factory = None
        return result

    def add_to_my_list(
        self,
        episode_id: int,
        episode_title: str,
        feed_id: int | None,
        feed_title: str | None,
        image: str | None,
        url: str | None,
    ):
        """Add an episode to My List (ignore if already present)."""
        self.conn.execute(
            """
            INSERT OR IGNORE INTO my_list
                (episode_id, episode_title, feed_id, feed_title, image, url)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (episode_id, episode_title, feed_id, feed_title, image, url),
        )
        self.conn.commit()

    def remove_from_my_list(self, episode_id: int):
        """Remove an episode from My List."""
        self.conn.execute("DELETE FROM my_list WHERE episode_id = ?", (episode_id,))
        self.conn.commit()

    # --- Trending and Reddit Caches ---

    def set_trending_cache(self, cache_type: str, data: dict) -> None:
        """Store trending cache data"""
        import json
        self.conn.execute(
            """INSERT OR REPLACE INTO trending_cache (cache_type, data, cached_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            (cache_type, json.dumps(data)),
        )
        self.conn.commit()

    def get_trending_cache(self, cache_type: str) -> dict | None:
        """Retrieve trending cache with timestamp"""
        import json
        from datetime import datetime, timezone

        row = self.conn.execute(
            "SELECT data, cached_at FROM trending_cache WHERE cache_type = ?",
            (cache_type,),
        ).fetchone()

        if not row:
            return None

        # Parse the timestamp and add UTC timezone info
        cached_at = datetime.fromisoformat(row[1])
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)

        return {
            **json.loads(row[0]),
            "cached_at": cached_at,
        }

    def is_trending_cache_stale(self, cache_type: str, max_age_seconds: int) -> bool:
        """Check if trending cache is stale"""
        from datetime import datetime, timedelta, timezone

        cached = self.get_trending_cache(cache_type)
        if not cached:
            return True

        age = datetime.now(timezone.utc) - cached["cached_at"]
        return age > timedelta(seconds=max_age_seconds)

    def update_reddit_mention(
        self, podcast_name: str, subreddits: list[str], increment: int = 1
    ) -> None:
        """Update or insert Reddit mention count"""
        import json

        podcast_name = podcast_name.lower()  # Normalize to lowercase
        subreddits_json = json.dumps(subreddits)

        # Try to update existing
        cursor = self.conn.execute(
            """UPDATE reddit_mentions
               SET mention_count = mention_count + ?,
                   subreddits = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE podcast_name = ?""",
            (increment, subreddits_json, podcast_name),
        )

        # If no rows updated, insert new
        if cursor.rowcount == 0:
            self.conn.execute(
                """INSERT INTO reddit_mentions (podcast_name, mention_count, subreddits)
                   VALUES (?, ?, ?)""",
                (podcast_name, increment, subreddits_json),
            )

        self.conn.commit()

    def get_reddit_mentions(self, max_age_hours: int = 24) -> dict[str, int]:
        """Get Reddit mentions within max age"""
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        rows = self.conn.execute(
            """SELECT podcast_name, mention_count
               FROM reddit_mentions
               WHERE updated_at > ?""",
            (cutoff.isoformat(),),
        ).fetchall()

        return {row[0]: row[1] for row in rows}
