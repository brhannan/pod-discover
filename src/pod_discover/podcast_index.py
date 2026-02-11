import hashlib
import os
import time
from typing import Any

import httpx

from .models import Episode


class PodcastIndexClient:
    """Async client for Podcast Index API with proper authentication."""

    BASE_URL = "https://api.podcastindex.org/api/1.0"

    def __init__(self, api_key: str | None = None, api_secret: str | None = None):
        self.api_key = api_key or os.getenv("PODCAST_INDEX_KEY", "")
        self.api_secret = api_secret or os.getenv("PODCAST_INDEX_SECRET", "")
        if not self.api_key or not self.api_secret:
            raise ValueError("PODCAST_INDEX_KEY and PODCAST_INDEX_SECRET must be set")

    def _get_auth_headers(self) -> dict[str, str]:
        """Generate authentication headers with timestamp and hash."""
        unix_time = str(int(time.time()))
        data_to_hash = self.api_key + self.api_secret + unix_time
        hash_value = hashlib.sha1(data_to_hash.encode()).hexdigest()

        return {
            "User-Agent": "pod-discover/0.1.0",
            "X-Auth-Key": self.api_key,
            "X-Auth-Date": unix_time,
            "Authorization": hash_value,
        }

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict:
        """Make authenticated GET request to Podcast Index API."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_auth_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params or {}, timeout=30.0)
            response.raise_for_status()
            return response.json()

    def _parse_episode(self, item: dict, feed_title_fallback: str = "") -> Episode:
        """Parse raw API episode data into Episode model."""
        return Episode(
            id=item.get("id", 0),
            title=item.get("title", ""),
            description=item.get("description", ""),
            feed_title=item.get("feedTitle", "") or feed_title_fallback,
            feed_id=item.get("feedId") or item.get("feedId"),
            duration_seconds=item.get("duration"),
            date_published=str(item.get("datePublished", "")),
            url=item.get("link", "") or item.get("enclosureUrl", ""),
            image=item.get("feedImage") or item.get("image") or item.get("artwork"),
            transcript_url=item.get("transcriptUrl"),
        )

    async def _search_feeds(self, query: str, max_feeds: int = 5) -> list[dict]:
        """Search for podcast feeds, trying the full query first then individual words."""
        feed_data = await self._get("search/byterm", {"q": query, "max": max_feeds})
        feeds = feed_data.get("feeds", [])
        if feeds:
            return feeds

        # Full query returned nothing — try individual words for multi-word queries
        words = query.split()
        if len(words) <= 1:
            return []

        seen_ids: set[int] = set()
        all_feeds: list[dict] = []
        for word in words:
            if len(word) < 3:
                continue
            data = await self._get("search/byterm", {"q": word, "max": 3})
            for feed in data.get("feeds", []):
                fid = feed.get("id")
                if fid and fid not in seen_ids:
                    seen_ids.add(fid)
                    all_feeds.append(feed)
        return all_feeds[:max_feeds]

    async def search_episodes_by_term(self, query: str, max_results: int = 10) -> list[Episode]:
        """Search by term: finds matching podcasts, then returns recent episodes from each."""
        feeds = await self._search_feeds(query)
        if not feeds:
            return []

        episodes: list[Episode] = []
        eps_per_feed = max(2, max_results // len(feeds))
        for feed in feeds:
            feed_id = feed.get("id")
            feed_title = feed.get("title", "")
            if not feed_id:
                continue
            ep_data = await self._get("episodes/byfeedid", {"id": feed_id, "max": eps_per_feed})
            for item in ep_data.get("items", []):
                episodes.append(self._parse_episode(item, feed_title_fallback=feed_title))
                if len(episodes) >= max_results:
                    return episodes

        return episodes

    async def get_episode_by_id(self, episode_id: int) -> Episode | None:
        """Get full details for a specific episode."""
        data = await self._get("episodes/byid", {"id": episode_id})
        episode_data = data.get("episode")
        return self._parse_episode(episode_data) if episode_data else None

    async def get_episodes_by_feed(self, feed_id: int, max_results: int = 20) -> list[Episode]:
        """List recent episodes from a specific podcast feed."""
        data = await self._get("episodes/byfeedid", {"id": feed_id, "max": max_results})
        items = data.get("items", [])
        return [self._parse_episode(item) for item in items[:max_results]]

    async def search_episodes_by_person(self, person: str, max_results: int = 10) -> list[Episode]:
        """Find episodes featuring a specific person."""
        data = await self._get("search/byperson", {"q": person, "max": max_results, "fulltext": "true"})
        items = data.get("items", [])
        return [self._parse_episode(item) for item in items[:max_results]]

    async def get_random_episodes(
        self, max_results: int = 5, category: str | None = None, lang: str = "en"
    ) -> list[Episode]:
        """Get random episodes, optionally filtered by category."""
        params: dict[str, Any] = {"max": max_results, "lang": lang}
        if category:
            params["cat"] = category

        data = await self._get("episodes/random", params)
        items = data.get("episodes", [])
        return [self._parse_episode(item) for item in items[:max_results]]
