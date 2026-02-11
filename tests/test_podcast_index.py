import pytest
from unittest.mock import AsyncMock, patch

from pod_discover.podcast_index import PodcastIndexClient
from pod_discover.models import Episode


@pytest.fixture
def mock_client():
    """Create a PodcastIndexClient with mock credentials."""
    with patch.dict("os.environ", {"PODCAST_INDEX_KEY": "test_key", "PODCAST_INDEX_SECRET": "test_secret"}):
        return PodcastIndexClient()


@pytest.mark.asyncio
async def test_search_episodes_by_term(mock_client):
    """Test searching episodes by term."""
    mock_response = {
        "items": [
            {
                "id": 123,
                "title": "Test Episode",
                "description": "A test episode",
                "feedTitle": "Test Podcast",
                "feedId": 456,
                "duration": 3600,
                "datePublished": 1234567890,
                "link": "https://example.com/episode",
                "feedImage": "https://example.com/image.jpg",
            }
        ]
    }

    with patch.object(mock_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        episodes = await mock_client.search_episodes_by_term("test query", max_results=10)

        assert len(episodes) == 1
        assert isinstance(episodes[0], Episode)
        assert episodes[0].id == 123
        assert episodes[0].title == "Test Episode"
        assert episodes[0].feed_title == "Test Podcast"
        mock_get.assert_called_once_with("search/byterm", {"q": "test query", "max": 10, "fulltext": "true"})


@pytest.mark.asyncio
async def test_get_episode_by_id(mock_client):
    """Test getting episode by ID."""
    mock_response = {
        "episode": {
            "id": 789,
            "title": "Specific Episode",
            "description": "Episode description",
            "feedTitle": "Podcast Name",
        }
    }

    with patch.object(mock_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        episode = await mock_client.get_episode_by_id(789)

        assert episode is not None
        assert episode.id == 789
        assert episode.title == "Specific Episode"
        mock_get.assert_called_once_with("episodes/byid", {"id": 789})


@pytest.mark.asyncio
async def test_get_episode_by_id_not_found(mock_client):
    """Test getting episode by ID when not found."""
    mock_response = {"episode": None}

    with patch.object(mock_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        episode = await mock_client.get_episode_by_id(999)

        assert episode is None


@pytest.mark.asyncio
async def test_search_by_person(mock_client):
    """Test searching episodes by person."""
    mock_response = {
        "items": [
            {"id": 111, "title": "Interview Episode", "description": "With special guest", "feedTitle": "Interview Show"}
        ]
    }

    with patch.object(mock_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        episodes = await mock_client.search_episodes_by_person("John Doe", max_results=10)

        assert len(episodes) == 1
        assert episodes[0].id == 111
        mock_get.assert_called_once_with("search/byperson", {"q": "John Doe", "max": 10, "fulltext": "true"})


@pytest.mark.asyncio
async def test_get_random_episodes(mock_client):
    """Test getting random episodes."""
    mock_response = {
        "episodes": [
            {"id": 222, "title": "Random Episode 1", "description": "First random", "feedTitle": "Random Show"},
            {"id": 333, "title": "Random Episode 2", "description": "Second random", "feedTitle": "Another Show"},
        ]
    }

    with patch.object(mock_client, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        episodes = await mock_client.get_random_episodes(max_results=5, category="Technology")

        assert len(episodes) == 2
        assert episodes[0].id == 222
        assert episodes[1].id == 333
        mock_get.assert_called_once_with("episodes/random", {"max": 5, "lang": "en", "cat": "Technology"})


def test_client_requires_credentials():
    """Test that client raises error without credentials."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="PODCAST_INDEX_KEY and PODCAST_INDEX_SECRET must be set"):
            PodcastIndexClient()
