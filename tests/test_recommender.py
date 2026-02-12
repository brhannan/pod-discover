# tests/test_recommender.py
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pod_discover.recommender import Recommender
from pod_discover.models import Episode
from pod_discover.db import Database


@pytest.fixture
def mock_db():
    """Mock database for testing"""
    db = Mock(spec=Database)

    # Mock taste profile
    db.get_taste_profile.return_value = Mock(
        model_dump_json=Mock(return_value='{"interests": ["tech", "science"]}')
    )

    # Mock favorites
    db.get_favorite_feeds.return_value = [
        {"feed_id": 100, "feed_title": "Tech Podcast"}
    ]

    # Mock history
    db.get_consumption_history.return_value = []

    # Mock cache
    db.get_cached_recommendations.return_value = None
    db.set_cached_recommendations = Mock()

    # Mock trending cache
    db.is_trending_cache_stale.return_value = False
    db.get_trending_cache.return_value = {
        "podcasts": {
            100: {"title": "Trending Podcast 1"},
            200: {"title": "Trending Podcast 2"},
        },
        "episodes": {
            1001: {"rank": 0},
            1002: {"rank": 1},
        },
    }

    # Mock Reddit mentions
    db.get_reddit_mentions.return_value = {
        "tech podcast": 15,
        "science show": 8,
    }

    return db


@pytest.fixture
def mock_podcast_client():
    """Mock podcast index client for testing"""
    client = Mock()

    # Mock search results
    async def mock_search(query, max_results=5):
        return [
            Episode(
                id=1001,
                title=f"Episode about {query}",
                description="Description",
                feed_id=100,
                feed_title="Tech Podcast",
                duration_seconds=1800,
                date_published="2025-01-15T10:00:00Z",
                image="https://example.com/image.jpg",
                url="https://example.com/episode1",
            )
        ]

    client.search_episodes_by_term = AsyncMock(side_effect=mock_search)

    # Mock episodes by feed ID
    async def mock_episodes_by_feed(feed_id, max_results=3):
        return [
            Episode(
                id=2000 + feed_id,
                title=f"Episode from feed {feed_id}",
                description="Description",
                feed_id=feed_id,
                feed_title=f"Podcast {feed_id}",
                duration_seconds=1800,
                date_published="2025-01-15T10:00:00Z",
                image="https://example.com/image.jpg",
                url=f"https://example.com/episode{feed_id}",
            )
        ]

    client.get_episodes_by_feed_id = AsyncMock(side_effect=mock_episodes_by_feed)

    # Mock trending episodes
    async def mock_trending_episodes(max_results=20):
        return [
            Episode(
                id=3001,
                title="Trending Episode 1",
                description="Description",
                feed_id=300,
                feed_title="Trending Podcast",
                duration_seconds=1800,
                date_published="2025-01-15T10:00:00Z",
                image="https://example.com/image.jpg",
                url="https://example.com/trending1",
            )
        ]

    client.get_trending_episodes = AsyncMock(side_effect=mock_trending_episodes)

    return client


@pytest.mark.asyncio
async def test_recommend_gathers_from_multiple_sources(mock_db, mock_podcast_client):
    """Test that recommender gathers candidates from all 4 sources"""
    recommender = Recommender(db=mock_db, podcast_client=mock_podcast_client, api_key="test-key")

    # Mock Claude API calls
    with patch.object(recommender, '_call_claude') as mock_claude:
        # First call: return search queries
        # Second call: return rankings
        mock_claude.side_effect = [
            ('["tech news", "science"]', {"input_tokens": 100, "output_tokens": 20}),
            ('[{"id": 1001, "score": 8, "reason": "Great match"}]', {"input_tokens": 200, "output_tokens": 50}),
        ]

        result = await recommender.recommend("show me tech podcasts")

        # Verify all sources were called
        # 1. AI search queries were used
        assert mock_podcast_client.search_episodes_by_term.called

        # 2. Trending episodes were fetched
        assert mock_podcast_client.get_trending_episodes.called

        # 3. Trending feeds were fetched
        assert mock_db.get_trending_cache.called

        # 4. Reddit mentions were fetched
        assert mock_db.get_reddit_mentions.called


@pytest.mark.asyncio
async def test_recommend_uses_composite_scoring(mock_db, mock_podcast_client):
    """Test that recommender applies composite scoring to candidates"""
    recommender = Recommender(db=mock_db, podcast_client=mock_podcast_client, api_key="test-key")

    # Mock Claude API calls
    with patch.object(recommender, '_call_claude') as mock_claude:
        mock_claude.side_effect = [
            ('["tech"]', {"input_tokens": 100, "output_tokens": 20}),
            ('[{"id": 1001, "score": 8, "reason": "Great match"}]', {"input_tokens": 200, "output_tokens": 50}),
        ]

        # Mock the composite scoring function to track if it's called
        with patch('pod_discover.recommender.calculate_composite_score') as mock_composite:
            mock_composite.return_value = 0.85

            result = await recommender.recommend("tech news")

            # Verify composite scoring was used
            assert mock_composite.called

            # Verify result contains episodes with composite scores
            assert "episodes" in result
            if result["episodes"]:
                # Check that composite_score is present in episode data
                episode = result["episodes"][0]
                assert "match_score" in episode
                assert 0 <= episode["match_score"] <= 10
