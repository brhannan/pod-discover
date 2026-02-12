# Recommendation Algorithm Redesign

**Date:** 2026-02-11
**Status:** Approved
**Goal:** Improve podcast recommendations by incorporating trending signals, social buzz, and collaborative filtering

## Problem Statement

Current recommendations rely solely on AI-generated queries based on user profile, favorites, and history. Users report recommendations are "missing my taste" - not aligning with actual interests despite having profile data and favorites configured.

## Solution Overview

Implement a hybrid recommendation system that blends personalized AI recommendations (70%) with discovery signals from trending content and social proof (30%).

### Key Additions

1. **Podcast Index trending data** - Surface what's currently popular
2. **Reddit community mentions** - Incorporate social buzz from podcast communities
3. **Popularity/quality signals** - Use download counts and episode counts as quality proxies
4. **Composite scoring** - Weight multiple signals to balance personalization with discovery
5. **Rich visualizations** - Educational "Why This?" system showing how recommendations were generated

---

## Architecture

### Current System
```
User Profile → Claude (generate queries) → Podcast Index Search → Claude (rank) → Recommendations
```

### New System
```
User Profile + Favorites + History
    ↓
[Signal Gathering Phase]
├─ Claude generates personalized queries → Podcast Index Search
├─ Podcast Index /podcasts/trending → Trending feeds
├─ Podcast Index /episodes/trending → Trending episodes
└─ Reddit RSS parser → Community-recommended podcasts
    ↓
[Candidate Pool]
Merge all episodes, dedupe by ID
    ↓
[Scoring & Ranking Phase]
Calculate composite score for each episode:
- AI match score (from Claude analysis)
- Trending boost (if in trending feeds/episodes)
- Social boost (if mentioned on Reddit)
- Download count boost (from feed metadata)
    ↓
[Final Selection]
Sort by composite score → Dedupe by feed → Top 6-10 episodes
```

### Key Changes

1. **Multi-source candidate gathering** instead of just AI queries
2. **Composite scoring** that blends AI understanding with popularity signals
3. **Reddit cache** (refresh every 6 hours) to avoid rate limits
4. **Trending cache** (refresh every 4 hours) since trending changes slowly

---

## Data Sources

### Podcast Index API (New Endpoints)

**1. `/podcasts/trending`**
- Returns: List of trending podcast feeds with metadata
- Fields needed: `id`, `title`, `newestItemPublishTime`, `trendScore`
- Refresh: Every 4 hours
- Use: Identify hot podcasts to boost in ranking

**2. `/episodes/trending`**
- Returns: List of trending episodes
- Fields: `id`, `title`, `feedId`, `feedTitle`, `trendScore`
- Refresh: Every 4 hours
- Use: Direct candidates for recommendation pool

**3. Enhanced feed metadata**
- Add to parsing: `download_count`, `episodeCount`, `categories`, `trendScore`
- Already available in API responses but not currently captured

### Reddit RSS Integration

**Subreddits to monitor:**
- `/r/podcasts/hot.rss` - General podcast discussions
- `/r/podcasts/top.rss?t=week` - Top weekly posts
- Optionally: Niche subreddits based on user topic interests

**RSS parsing approach:**
- Extract post titles and content
- Use regex to find podcast names
- Track mention frequency over rolling 7-day window
- Store: `{podcast_name: mention_count, last_seen: timestamp}`

**Matching:**
- Fuzzy-match candidate episode `feed_title` against Reddit mentions
- Boost score if found in Reddit data

### Database Schema Updates

```sql
-- Trending cache
CREATE TABLE IF NOT EXISTS trending_cache (
    cache_type TEXT PRIMARY KEY,  -- 'podcasts' or 'episodes'
    data JSON NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reddit mentions cache
CREATE TABLE IF NOT EXISTS reddit_mentions (
    podcast_name TEXT PRIMARY KEY,
    mention_count INTEGER DEFAULT 1,
    subreddits TEXT,  -- JSON array
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Recommendation Flow

### Phase 1: Check Cache
```python
profile_hash = hash(profile + favorites + history + user_request)
cached_recs = db.get_cached_recommendations(profile_hash)
if cached_recs and age < 1_hour:
    return cached_recs
```

### Phase 2: Gather Candidates (parallel fetching)

```python
# All run concurrently
candidates = await gather(
    # Existing: AI-generated queries
    get_ai_query_candidates(profile, favorites, history, user_request),

    # New: Trending episodes (direct candidates)
    get_trending_episodes(max=10),

    # New: Episodes from trending podcasts
    get_episodes_from_trending_feeds(max_feeds=5, episodes_per_feed=2),

    # New: Episodes from Reddit-mentioned podcasts
    get_episodes_from_reddit_podcasts(max_feeds=3, episodes_per_feed=2),
)

all_episodes = dedupe_by_id(flatten(candidates))
# Typical pool size: 25-40 episodes
```

### Phase 3: Score & Rank

```python
for episode in all_episodes:
    score = calculate_composite_score(
        episode=episode,
        ai_scores=ai_rankings,
        trending_data=trending_cache,
        reddit_data=reddit_mentions,
        user_profile=profile,
    )
    episode.composite_score = score
    episode.score_breakdown = {...}

ranked = sort(all_episodes, key=lambda e: e.composite_score, reverse=True)
```

### Phase 4: Dedupe, Enrich & Return

```python
final = dedupe_by_feed(ranked, max_results=10)

# Add visualization metadata
for episode in final:
    episode.signal_breakdown = {
        "ai_match": episode.ai_score / 10,
        "trending": episode.trending_boost,
        "reddit_buzz": episode.reddit_boost,
        "popularity": episode.popularity_boost,
    }
    episode.discovery_metadata = {...}  # For visualizations

return {
    "episodes": final,
    "meta": {
        "queries_used": ai_queries,
        "sources": {
            "ai_personalized": count_by_source(final, "ai"),
            "trending": count_by_source(final, "trending"),
            "reddit": count_by_source(final, "reddit"),
        },
        "total_candidates_considered": len(all_episodes),
    },
    "usage": claude_usage,
    "cached": False,
}
```

---

## Composite Scoring Algorithm

### Weight Distribution

```
AI Match:        50%  ─┐
Duration Match:   5%  ├─ 70% Personalized (approx)
Recency:         10%  ─┘

Trending:        15%  ─┐
Social Buzz:     10%  ├─ 30% Discovery/Social Proof
Popularity:      10%  ─┘
                 ─────
Total:          100%
```

### Calculation

```python
def calculate_composite_score(
    episode: Episode,
    ai_score: float,  # 0-10 from Claude ranking
    trending_data: dict,
    reddit_data: dict,
    feed_metadata: dict,
) -> float:
    """Composite score blending personalization + discovery signals."""

    # Import weights from config
    from .config import RecommendationWeights as W

    composite = (
        (ai_score / 10.0) * W.AI_MATCH +
        calculate_trending_score(episode, trending_data) * W.TRENDING +
        calculate_social_score(episode, reddit_data) * W.SOCIAL_BUZZ +
        calculate_popularity_score(episode, feed_metadata) * W.POPULARITY +
        calculate_recency_score(episode) * W.RECENCY +
        calculate_duration_match(episode, user_profile) * W.DURATION_MATCH
    ) * 10

    return composite
```

### Individual Scoring Functions

**Trending Score (0-1):**
```python
def calculate_trending_score(episode: Episode, trending_data: dict) -> float:
    # Episode itself is trending
    if episode.id in trending_data['episodes']:
        trend_rank = trending_data['episodes'][episode.id]['rank']
        return 1.0 - (trend_rank / 100)  # Top 10 = 0.9+

    # Podcast feed is trending
    if episode.feed_id in trending_data['podcasts']:
        feed_rank = trending_data['podcasts'][episode.feed_id]['rank']
        return 0.5 * (1.0 - (feed_rank / 100))  # Half weight

    return 0.0
```

**Social Buzz Score (0-1):**
```python
def calculate_social_score(episode: Episode, reddit_data: dict) -> float:
    feed_title = episode.feed_title.lower()

    # Fuzzy match against Reddit mentions
    for mentioned_podcast, mention_count in reddit_data.items():
        similarity = fuzzy_match(feed_title, mentioned_podcast)
        if similarity > 0.85:
            return min(mention_count / 10.0, 1.0)  # 10+ mentions = max

    return 0.0
```

**Popularity Score (0-1):**
```python
def calculate_popularity_score(episode: Episode, feed_metadata: dict) -> float:
    if not episode.feed_id:
        return 0.3  # Neutral

    episode_count = feed_metadata[episode.feed_id].get('episode_count', 0)
    return min(episode_count / 500, 1.0)  # 500+ episodes = max
```

**Recency Score (0-1):**
```python
def calculate_recency_score(episode: Episode) -> float:
    days_old = (datetime.now() - parse_date(episode.date_published)).days

    if days_old <= 7: return 1.0
    elif days_old <= 30: return 0.8
    elif days_old <= 90: return 0.5
    else: return 0.2
```

**Duration Match (0-1):**
```python
def calculate_duration_match(episode: Episode, profile: TasteProfile) -> float:
    if not episode.duration_seconds:
        return 0.5  # Unknown = neutral

    duration_min = episode.duration_seconds / 60
    pref_min = profile.preferred_duration_min
    pref_max = profile.preferred_duration_max

    if not pref_min and not pref_max:
        return 0.5  # No preference

    if pref_min <= duration_min <= pref_max:
        return 1.0  # Perfect match

    # Penalize based on distance from range
    distance = min(abs(duration_min - pref_min), abs(duration_min - pref_max))
    return max(0.0, 1.0 - (distance / 60))
```

---

## Configuration System

### config.py

```python
"""
Recommendation System Configuration

SCORING WEIGHTS:
These weights control how different signals influence recommendations.
Total must sum to 1.0 (100%).
"""

class RecommendationWeights:
    # Personalization signals (70% total)
    AI_MATCH = 0.50
    DURATION_MATCH = 0.05
    RECENCY = 0.10

    # Discovery signals (30% total)
    TRENDING = 0.15
    SOCIAL_BUZZ = 0.10
    POPULARITY = 0.10

    @classmethod
    def validate(cls):
        """Ensure weights sum to 1.0"""
        total = sum([
            cls.AI_MATCH, cls.DURATION_MATCH, cls.RECENCY,
            cls.TRENDING, cls.SOCIAL_BUZZ, cls.POPULARITY,
        ])
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total}"
        return True

# Validate on import
RecommendationWeights.validate()

# Cache TTLs
TRENDING_CACHE_TTL = 4 * 60 * 60  # 4 hours
REDDIT_CACHE_TTL = 6 * 60 * 60    # 6 hours
REC_CACHE_TTL = 1 * 60 * 60       # 1 hour

# Reddit subreddits to monitor
REDDIT_SUBREDDITS = ["podcasts", "TrueCrimePodcasts"]
```

**Tuning:** Edit weights in `config.py` and restart server. The system validates that weights sum to 1.0 on startup.

---

## Visualization System

### "Why This?" Educational Component

Each recommendation includes rich metadata for visualization:

```python
episode.discovery_metadata = {
    "discovery_path": {
        "source": "ai_query",  # or "trending", "reddit"
        "query": "investigative journalism",
        "hops": [
            {"step": "profile_topic", "value": "true crime", "weight": 0.8},
            {"step": "query_generation", "value": "investigative journalism"},
            {"step": "search_result", "rank": 3},
            {"step": "trending_boost", "value": "+15%"},
        ]
    },
    "score_dimensions": {
        "ai_match": 8.5,
        "trending": 7.2,
        "social_buzz": 6.8,
        "popularity": 8.1,
        "recency": 9.0,
    },
    "connections": {
        "similar_to_favorites": ["Serial", "This American Life"],
        "shared_topics": ["investigative", "narrative", "true crime"],
        "reddit_subreddits": ["r/podcasts", "r/truecrime"],
    },
    "ranking_context": {
        "total_candidates": 38,
        "this_rank": 2,
        "percentile": 95,
    }
}
```

### Visualization Components

**1. Discovery Flow Diagram** (Sankey/flowchart)
Shows the path from user profile → AI query → search → boost → final recommendation

**2. Multi-Dimensional Radar Chart**
6 dimensions radiating from center: AI Match, Trending, Social Buzz, Popularity, Recency, Duration Match

**3. Network Graph**
Shows connections between user's favorite podcasts and recommended content via shared topics/guests

**4. Source Attribution Bar**
Stacked horizontal bar showing contribution of each signal to final score

**5. Competitive Ranking View**
Visual bar chart showing where this episode ranks among all candidates

### UI Layout

```
┌─────────────────────────────────────┐
│ [Episode Card - collapsed]          │
│ 🎯 8.7/10 Match                     │
│ [▸ Why This?] ◄── Expandable       │
└─────────────────────────────────────┘

Expanded:
┌─────────────────────────────────────┐
│ HOW WE FOUND THIS                   │
│ [Discovery Flow Diagram]            │
│                                      │
│ MATCH BREAKDOWN                     │
│ [Radar Chart]                       │
│                                      │
│ CONNECTIONS                         │
│ [Network Graph]                     │
│                                      │
│ STANDING                            │
│ Ranked #2 of 38 candidates          │
│ [Competitive bar chart]             │
└─────────────────────────────────────┘
```

**Tech:** D3.js or Recharts for client-side visualization rendering

---

## Caching Strategy

### Cache Layers

**1. Trending Data Cache**
- Table: `trending_cache` (cache_type, data JSON, cached_at)
- TTL: 4 hours
- Stores: Top 100 trending podcasts and episodes from Podcast Index

**2. Reddit Mentions Cache**
- Table: `reddit_mentions` (podcast_name, mention_count, subreddits, last_seen)
- TTL: 6 hours
- Stores: Podcast mention counts from RSS feed parsing

**3. Recommendation Cache** (existing)
- Table: `recommendation_cache` (profile_hash, user_request, result, cached_at)
- TTL: 1 hour
- Invalidates when: User updates profile, adds favorite, or rates episode

### Background Refresh

```python
async def background_cache_refresh():
    while True:
        await asyncio.sleep(4 * 60 * 60)  # 4 hours
        try:
            await refresh_trending_cache()
        except Exception as e:
            logger.error(f"Trending refresh failed: {e}")

        await asyncio.sleep(2 * 60 * 60)  # 2 more hours (total 6)
        try:
            await refresh_reddit_cache()
        except Exception as e:
            logger.error(f"Reddit refresh failed: {e}")
```

Added to server lifespan as background task.

### Performance Targets

- **Cold start** (no cache): ~3-5 seconds
- **Warm cache** (recommendation cached): ~50-100ms
- **Partial cache** (trending/reddit cached): ~2-3 seconds

---

## Implementation Plan

### Phase 1: Infrastructure & Data Sources

**1.1 Add Podcast Index endpoints**
- `get_trending_podcasts()` in `podcast_index.py`
- `get_trending_episodes()` in `podcast_index.py`
- Enhance `_parse_episode()` to capture trend scores

**1.2 Database schema updates**
- Create `trending_cache` table
- Create `reddit_mentions` table
- Add DB methods for cache operations

**1.3 Reddit RSS parser**
- Create `reddit_parser.py` module
- RSS feed fetching for multiple subreddits
- Extract podcast mentions with regex + fuzzy matching

**1.4 Configuration system**
- Create `config.py` with `RecommendationWeights`
- Add validation logic
- Document parameters

### Phase 2: Recommendation Engine Updates

**2.1 Multi-source candidate gathering**
- Refactor `recommend()` for multiple sources
- Add `get_trending_candidates()`
- Add `get_reddit_candidates()`
- Parallel fetching with `asyncio.gather()`

**2.2 Composite scoring system**
- Implement individual scoring functions
- Implement `calculate_composite_score()`
- Add score breakdown metadata

**2.3 Discovery metadata enrichment**
- Add `discovery_metadata` to responses
- Capture path/connections/context during flow

### Phase 3: Background Jobs & Caching

**3.1 Cache refresh logic**
- `refresh_trending_cache()` function
- `refresh_reddit_cache()` function
- Error handling and logging

**3.2 Background task runner**
- Add to server lifespan
- Configure intervals (4h/6h)
- Graceful shutdown

**3.3 Cache invalidation**
- Update endpoints to invalidate rec cache
- Add cache hit/miss logging

### Phase 4: API & Frontend Updates

**4.1 Update recommendation API response**
- Add `meta` object
- Add `signal_breakdown` per episode
- Add `discovery_metadata`

**4.2 Frontend visualization components**
- `DiscoveryFlowDiagram.jsx` (Sankey)
- `RadarScoreChart.jsx` (multi-dimensional)
- `NetworkGraph.jsx` (connections)
- `RankingBar.jsx` (competitive standing)

**4.3 "Why This?" expandable section**
- Expand/collapse UI in `RecommendationCard`
- Layout all visualization components
- Styling for dark theme

**4.4 Summary stats**
- Source breakdown display
- Badge system (🔥 Trending, 💬 Reddit, 🎯 Match)

### Phase 5: Testing & Documentation

**5.1 Testing**
- Unit tests for scoring functions
- Integration tests for multi-source gathering
- Cache refresh tests

**5.2 Documentation**
- Update README with algorithm explanation
- Document configuration options
- Add architecture diagram

**5.3 Monitoring**
- Logging for recommendation generation
- Cache hit rates
- Performance profiling

### Estimated Effort

- Phase 1: ~4-6 hours
- Phase 2: ~6-8 hours
- Phase 3: ~2-3 hours
- Phase 4: ~8-10 hours (visualizations are complex)
- Phase 5: ~3-4 hours

**Total: ~23-31 hours**

### Launch Strategy

**MVP (Phases 1-3):** Better recommendations working, basic frontend updates (scores, badges)

**Full Launch (All phases):** Complete visualization system with educational "Why This?" component

---

## Success Metrics

**Primary:**
- User satisfaction with recommendations (qualitative feedback)
- Click-through rate on recommendations
- Episodes added to "My List" from recommendations

**Secondary:**
- Source diversity (% from trending vs AI vs Reddit)
- Cache hit rates (should be >70% for trending/Reddit)
- Recommendation generation time (<3s for cold start)

**Monitoring:**
- Track which signals contribute most to final rankings
- Monitor Reddit mention counts and trending scores over time
- A/B test weight adjustments if needed
