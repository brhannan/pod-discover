# tests/test_reddit_parser.py
import pytest
from unittest.mock import patch, MagicMock
from pod_discover.reddit_parser import RedditParser


@pytest.fixture
def mock_feedparser():
    """Mock feedparser.parse to avoid real network calls"""
    with patch("pod_discover.reddit_parser.feedparser.parse") as mock_parse:
        yield mock_parse


def test_parse_subreddit_rss(mock_feedparser):
    """Test parsing a single subreddit RSS feed"""
    # Mock RSS response
    mock_entry = MagicMock()
    mock_entry.title = "I love the podcast 'Serial' - best true crime ever!"
    mock_entry.summary = "Serial is amazing. Also check out Criminal."

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]
    mock_feedparser.return_value = mock_feed

    parser = RedditParser()
    mentions = parser.parse_subreddit("podcasts")

    # Should extract "Serial" and "Criminal"
    assert "serial" in mentions
    assert "criminal" in mentions


def test_extract_podcast_names():
    """Test extracting podcast names from text"""
    parser = RedditParser()

    text = '''
    I really enjoy "Serial" and "This American Life".
    Also listening to Criminal these days.
    The podcast "Reply All" is great too.
    '''

    names = parser._extract_podcast_names(text)

    # Should find quoted names and capitalized standalone names
    assert "serial" in names
    assert "this american life" in names
    assert "criminal" in names
    assert "reply all" in names


def test_aggregate_mentions():
    """Test aggregating mentions from multiple sources"""
    parser = RedditParser()

    mentions_list = [
        {"serial": 3, "criminal": 2},
        {"serial": 1, "radiolab": 1},
        {"criminal": 1},
    ]

    result = parser._aggregate_mentions(mentions_list)

    assert result["serial"] == 4
    assert result["criminal"] == 3
    assert result["radiolab"] == 1


def test_parse_multiple_subreddits(mock_feedparser):
    """Test parsing multiple subreddits"""
    mock_entry = MagicMock()
    mock_entry.title = "Love the podcast Serial"
    mock_entry.summary = ""

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]
    mock_feedparser.return_value = mock_feed

    parser = RedditParser()
    mentions = parser.parse_subreddits(["podcasts", "TrueCrimePodcasts"])

    # Should aggregate from both subreddits
    assert "serial" in mentions
    assert mentions["serial"] >= 1
    assert mock_feedparser.call_count == 2
