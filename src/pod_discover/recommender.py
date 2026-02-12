"""AI-powered recommendation engine using Claude."""

import asyncio
import hashlib
import json
import os

import anthropic

from .config import REDDIT_SUBREDDITS, TRENDING_CACHE_TTL
from .db import Database
from .models import Episode, TasteProfile
from .podcast_index import PodcastIndexClient
from .scoring import calculate_composite_score

SEARCH_PROMPT = """\
You are a podcast recommendation engine. Given a user's taste profile, favorite podcasts, and listening history, \
generate search queries to find podcast episodes they'd love.

<taste_profile>
{profile}
</taste_profile>

<favorite_podcasts>
{favorites}
</favorite_podcasts>

<recent_history>
{history}
</recent_history>

{user_request}

Generate 3-5 search queries that would find great podcast episodes for this user. \
Use their favorite podcasts as strong signals of what they enjoy — find similar content and adjacent topics. \
IMPORTANT: Keep queries SHORT — 2-3 words max. The search engine works best with concise terms. \
Each query should target a different angle or topic they'd enjoy. \
Return ONLY a JSON array of query strings, nothing else.

Example: ["quantum computing", "true crime", "startup founders", "space exploration", "Roman history"]"""

RANK_PROMPT = """\
You are a podcast recommendation engine. Rank and explain these episodes for the user based on their taste profile and favorite podcasts.

<taste_profile>
{profile}
</taste_profile>

<favorite_podcasts>
{favorites}
</favorite_podcasts>

<recent_history>
{history}
</recent_history>

<candidate_episodes>
{episodes}
</candidate_episodes>

For each episode worth recommending, return a JSON object with:
- "id": the episode id (number)
- "score": 1-10 match score
- "reason": 1-2 sentence explanation of why this matches their taste

Return a JSON array sorted by score descending. Only include episodes scoring 5+. \
If the user has no profile or history yet, score based on general quality/variety and say so in the reason.
Return ONLY the JSON array, no other text."""


class Recommender:
    def __init__(
        self,
        db: Database,
        podcast_client: PodcastIndexClient,
        api_key: str | None = None,
    ):
        self.db = db
        self.podcast_client = podcast_client
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""),
        )

    def _profile_summary(self) -> str:
        profile = self.db.get_taste_profile()
        return profile.model_dump_json(indent=2)

    def _favorites_summary(self) -> str:
        favs = self.db.get_favorite_feeds()
        if not favs:
            return "No favorite podcasts yet."
        return "\n".join(f"- {f['feed_title']}" for f in favs)

    def _history_summary(self) -> str:
        history = self.db.get_consumption_history(limit=15)
        if not history:
            return "No listening history yet."
        lines = []
        for e in history:
            line = f"- {e.title} (rated {e.rating}/5)"
            if e.notes:
                line += f" — {e.notes}"
            lines.append(line)
        return "\n".join(lines)

    def _call_claude(self, prompt: str) -> tuple[str, dict]:
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return response.content[0].text, usage

    def _parse_json(self, text: str):
        """Extract JSON from Claude's response, handling markdown fences."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())

    def _cache_key(self, profile: str, favorites: str, history: str, user_request: str) -> str:
        """Create a hash of the inputs to use as a cache key."""
        content = f"{profile}|{favorites}|{history}|{user_request}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def recommend(self, user_request: str = "") -> dict:
        profile = self._profile_summary()
        favorites = self._favorites_summary()
        history = self._history_summary()

        # Check cache first
        profile_hash = self._cache_key(profile, favorites, history, user_request)
        cached = self.db.get_cached_recommendations(profile_hash, user_request)
        if cached:
            result = json.loads(cached)
            result["cached"] = True
            return result

        # Step 1: Generate search queries
        request_text = f"The user says: \"{user_request}\"" if user_request else "No specific request — suggest based on their profile and favorite podcasts."
        search_prompt = SEARCH_PROMPT.format(
            profile=profile, favorites=favorites, history=history, user_request=request_text
        )
        queries_raw, search_usage = self._call_claude(search_prompt)
        queries = self._parse_json(queries_raw)
        total_usage = {
            "input_tokens": search_usage["input_tokens"],
            "output_tokens": search_usage["output_tokens"],
        }

        # Step 2: Gather candidates from multiple sources in parallel
        all_episodes: list[Episode] = []
        seen_ids: set[int] = set()

        # Gather from 4 sources in parallel
        results = await asyncio.gather(
            # Source 1: AI-generated search queries
            self._search_by_queries(queries[:5]),
            # Source 2: Trending episodes
            self.podcast_client.get_trending_episodes(max=10),
            # Source 3: Episodes from trending podcasts
            self._get_episodes_from_trending_feeds(),
            # Source 4: Episodes from Reddit-mentioned podcasts
            self._get_episodes_from_reddit_mentions(),
            return_exceptions=True,
        )

        # Combine all results, deduplicating by episode ID
        for result_set in results:
            if isinstance(result_set, Exception):
                # Log error but continue with other sources
                continue
            if isinstance(result_set, list):
                for ep in result_set:
                    if ep.id not in seen_ids:
                        seen_ids.add(ep.id)
                        all_episodes.append(ep)

        if not all_episodes:
            return {"episodes": [], "queries_used": queries, "usage": total_usage, "cached": False}

        # Get trending and Reddit data for scoring
        trending_data_raw = await self._get_trending_data()
        trending_data = trending_data_raw.get("podcasts", {})
        reddit_mentions = self.db.get_reddit_mentions(max_age_hours=24)

        # Step 3: Rank and explain with AI
        episodes_summary = json.dumps(
            [
                {
                    "id": ep.id,
                    "title": ep.title,
                    "description": ep.description[:300],
                    "feed_title": ep.feed_title,
                    "duration_seconds": ep.duration_seconds,
                }
                for ep in all_episodes
            ],
            indent=2,
        )
        rank_prompt = RANK_PROMPT.format(
            profile=profile, favorites=favorites, history=history, episodes=episodes_summary
        )
        rankings_raw, rank_usage = self._call_claude(rank_prompt)
        rankings = self._parse_json(rankings_raw)
        total_usage["input_tokens"] += rank_usage["input_tokens"]
        total_usage["output_tokens"] += rank_usage["output_tokens"]

        # Convert rankings to a dict for easier lookup
        ranking_dict = {r["id"]: r for r in rankings}

        # Build ranked episode list with composite scores (1 episode per feed)
        from .scoring import (
            calculate_trending_score,
            calculate_social_score,
            calculate_popularity_score,
            calculate_recency_score,
            calculate_duration_match,
        )

        ranked_episodes = []
        seen_feeds: set[int] = set()

        for ep in all_episodes:
            # Skip if we already have an episode from this feed
            if ep.feed_id and ep.feed_id in seen_feeds:
                continue

            # Get AI ranking (or default to 0 if not ranked)
            ai_ranking = ranking_dict.get(ep.id)
            if not ai_ranking:
                continue  # Skip episodes not ranked by AI

            ai_score = ai_ranking["score"] / 10.0  # Normalize to 0-1

            # Calculate all component scores
            trending_score = calculate_trending_score(ep.feed_id or 0, trending_data)
            social_score = calculate_social_score(ep.feed_title or "", reddit_mentions)
            popularity_score = calculate_popularity_score(ep)
            recency_score = calculate_recency_score(ep)
            duration_score = calculate_duration_match(ep, preferred_duration_minutes=30)

            # Calculate composite score
            composite_score = calculate_composite_score(
                episode=ep,
                trending_score=trending_score,
                social_score=social_score,
                popularity_score=popularity_score,
                recency_score=recency_score,
                duration_score=duration_score,
                ai_score=ai_score,
            )

            if ep.feed_id:
                seen_feeds.add(ep.feed_id)

            ranked_episodes.append({
                **ep.model_dump(),
                "match_score": ai_ranking["score"],
                "match_reason": ai_ranking["reason"],
                "composite_score": composite_score,
            })

        # Sort by composite score descending
        ranked_episodes.sort(key=lambda x: x["composite_score"], reverse=True)

        result = {
            "episodes": ranked_episodes,
            "queries_used": queries,
            "usage": total_usage,
            "cached": False,
        }

        # Store in cache
        self.db.set_cached_recommendations(profile_hash, user_request, json.dumps(result))

        return result

    async def _search_by_queries(self, queries: list[str]) -> list[Episode]:
        """Search for episodes using AI-generated queries."""
        episodes: list[Episode] = []
        seen_ids: set[int] = set()

        for q in queries:
            eps = await self.podcast_client.search_episodes_by_term(q, max_results=5)
            for ep in eps:
                if ep.id not in seen_ids:
                    seen_ids.add(ep.id)
                    episodes.append(ep)

        return episodes

    async def _get_episodes_from_trending_feeds(self) -> list[Episode]:
        """Get recent episodes from trending podcasts."""
        trending_data = await self._get_trending_data()
        trending_podcasts = trending_data.get("podcasts", {})

        if not trending_podcasts:
            return []

        # Get episodes from top 5 trending feeds
        tasks = []
        for feed_id in list(trending_podcasts.keys())[:5]:
            tasks.append(self.podcast_client.get_episodes_by_feed_id(feed_id, max_results=2))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        episodes: list[Episode] = []
        seen_ids: set[int] = set()

        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, list):
                for ep in result:
                    if ep.id not in seen_ids:
                        seen_ids.add(ep.id)
                        episodes.append(ep)

        return episodes

    async def _get_episodes_from_reddit_mentions(self) -> list[Episode]:
        """Get episodes from Reddit-mentioned podcasts."""
        reddit_mentions = self.db.get_reddit_mentions(max_age_hours=24)

        if not reddit_mentions:
            return []

        # Search for top mentioned podcasts
        tasks = []
        for podcast_name in list(reddit_mentions.keys())[:3]:
            tasks.append(self.podcast_client.search_episodes_by_term(podcast_name, max_results=2))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        episodes: list[Episode] = []
        seen_ids: set[int] = set()

        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, list):
                for ep in result:
                    if ep.id not in seen_ids:
                        seen_ids.add(ep.id)
                        episodes.append(ep)

        return episodes

    async def _get_trending_data(self) -> dict:
        """Get or refresh trending data cache."""
        # Check if cache is stale
        if self.db.is_trending_cache_stale("podcasts", TRENDING_CACHE_TTL):
            # Refresh cache
            podcasts = await self.podcast_client.get_trending_podcasts(max=100)
            episodes_list = await self.podcast_client.get_trending_episodes(max=100)

            # Convert episodes list to dict with ranks
            episodes = {}
            for rank, ep in enumerate(episodes_list):
                episodes[ep.id] = {"rank": rank}

            cache_data = {
                "podcasts": podcasts,  # Keep as dict from API
                "episodes": episodes,  # Dict mapping episode_id -> {rank}
            }

            self.db.set_trending_cache("podcasts", cache_data)
            return cache_data

        # Return cached data
        cached = self.db.get_trending_cache("podcasts")
        if cached:
            return cached

        # Fallback: return empty data
        return {"podcasts": {}, "episodes": {}}
