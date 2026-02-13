import tempfile
from pathlib import Path

import pytest

from pod_discover.db import Database
from pod_discover.models import ConsumptionEntry, TasteProfile


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        db = Database(db_path)
        yield db


def test_get_default_taste_profile(temp_db):
    """Test getting default taste profile."""
    profile = temp_db.get_taste_profile()
    assert isinstance(profile, TasteProfile)
    assert profile.preferred_depth == "moderate"
    assert profile.format_preferences == []
    assert profile.topic_interests == {}


def test_update_taste_profile(temp_db):
    """Test updating taste profile."""
    new_profile = TasteProfile(
        preferred_depth="deep-dive",
        format_preferences=["interview", "narrative"],
        topic_interests={"technology": 0.9, "history": 0.7},
        preferred_duration_min=30,
        preferred_duration_max=90,
        notes="Loves in-depth technical content",
    )

    temp_db.update_taste_profile(new_profile)
    retrieved = temp_db.get_taste_profile()

    assert retrieved.preferred_depth == "deep-dive"
    assert retrieved.format_preferences == ["interview", "narrative"]
    assert retrieved.topic_interests == {"technology": 0.9, "history": 0.7}
    assert retrieved.preferred_duration_min == 30
    assert retrieved.preferred_duration_max == 90
    assert retrieved.notes == "Loves in-depth technical content"


def test_log_consumption(temp_db):
    """Test logging consumption entry."""
    entry = ConsumptionEntry(
        item_id="12345",
        title="Great Episode",
        rating=5,
        notes="Really enjoyed this one",
    )

    entry_id = temp_db.log_consumption(entry)
    assert entry_id > 0

    history = temp_db.get_consumption_history(limit=1)
    assert len(history) == 1
    assert history[0].item_id == "12345"
    assert history[0].title == "Great Episode"
    assert history[0].rating == 5
    assert history[0].notes == "Really enjoyed this one"


def test_get_consumption_history(temp_db):
    """Test getting consumption history."""
    # Log multiple entries
    for i in range(5):
        entry = ConsumptionEntry(
            item_id=str(1000 + i),
            title=f"Episode {i}",
            rating=i % 5 + 1,
        )
        temp_db.log_consumption(entry)

    # Get all entries
    history = temp_db.get_consumption_history(limit=10)
    assert len(history) == 5

    # Check ordering (most recent first)
    assert history[0].title == "Episode 4"
    assert history[4].title == "Episode 0"

    # Test limit
    limited = temp_db.get_consumption_history(limit=3)
    assert len(limited) == 3


def test_consumption_entry_validation(temp_db):
    """Test that invalid ratings are rejected."""
    with pytest.raises(Exception):  # Pydantic validation error
        ConsumptionEntry(
            item_id="123",
            title="Bad Rating",
            rating=6,  # Invalid - must be 1-5
        )


def test_database_persistence(temp_db):
    """Test that data persists across Database instances."""
    # Create and update profile
    profile = TasteProfile(
        preferred_depth="casual",
        topic_interests={"science": 0.8},
    )
    temp_db.update_taste_profile(profile)

    # Log an entry
    entry = ConsumptionEntry(item_id="999", title="Persistent Episode", rating=4)
    temp_db.log_consumption(entry)

    # Create new Database instance with same path
    db2 = Database(temp_db.db_path)

    # Verify data persists
    retrieved_profile = db2.get_taste_profile()
    assert retrieved_profile.preferred_depth == "casual"
    assert retrieved_profile.topic_interests == {"science": 0.8}

    history = db2.get_consumption_history(limit=1)
    assert len(history) == 1
    assert history[0].item_id == "999"


def test_trending_cache_operations(tmp_path):
    """Test storing and retrieving trending cache"""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    # Set trending cache
    trending_data = {"feeds": [{"id": 123, "title": "Trending Show", "rank": 1}]}
    db.set_trending_cache("podcasts", trending_data)

    # Get trending cache
    cached = db.get_trending_cache("podcasts")
    assert cached is not None
    assert cached["feeds"][0]["id"] == 123

    # Check timestamp is recent
    from datetime import datetime, timezone
    assert (datetime.now(timezone.utc) - cached["cached_at"]).seconds < 5


def test_trending_cache_expiry(tmp_path):
    """Test that stale cache is identified"""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    trending_data = {"feeds": []}
    db.set_trending_cache("podcasts", trending_data)

    # Check if cache is stale (should not be within 1 second)
    assert not db.is_trending_cache_stale("podcasts", max_age_seconds=3600)


def test_reddit_mentions_operations(tmp_path):
    """Test storing and retrieving Reddit mentions"""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    # Update Reddit mentions
    db.update_reddit_mention("Serial", subreddits=["podcasts"], increment=5)
    db.update_reddit_mention("Criminal", subreddits=["TrueCrimePodcasts"], increment=3)

    # Get all mentions
    mentions = db.get_reddit_mentions(max_age_hours=24)
    assert "serial" in mentions  # Should be lowercase
    assert mentions["serial"] == 5
    assert mentions["criminal"] == 3
