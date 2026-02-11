"""AI-powered recommendation engine using Claude."""

import json
import os

import anthropic

from .db import Database
from .models import Episode, TasteProfile
from .podcast_index import PodcastIndexClient

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

    async def recommend(self, user_request: str = "") -> dict:
        profile = self._profile_summary()
        favorites = self._favorites_summary()
        history = self._history_summary()

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

        # Step 2: Search for episodes using generated queries
        all_episodes: list[Episode] = []
        seen_ids: set[int] = set()
        for q in queries[:5]:
            eps = await self.podcast_client.search_episodes_by_term(q, max_results=5)
            for ep in eps:
                if ep.id not in seen_ids:
                    seen_ids.add(ep.id)
                    all_episodes.append(ep)

        if not all_episodes:
            return {"episodes": [], "queries_used": queries, "usage": total_usage}

        # Step 3: Rank and explain
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

        # Build ranked episode list with reasons
        ranking_map = {r["id"]: r for r in rankings}
        ranked_episodes = []
        for r in rankings:
            ep = next((e for e in all_episodes if e.id == r["id"]), None)
            if ep:
                ranked_episodes.append({
                    **ep.model_dump(),
                    "match_score": r["score"],
                    "match_reason": r["reason"],
                })

        return {
            "episodes": ranked_episodes,
            "queries_used": queries,
            "usage": total_usage,
        }
