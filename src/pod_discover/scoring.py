# src/pod_discover/scoring.py
"""
Scoring functions for recommendation algorithm.

All scoring functions return normalized values between 0.0 and 1.0:
- 1.0 = perfect match/highest quality
- 0.0 = no match/lowest quality

These scores are combined using weighted averages defined in config.py
"""

import math
from datetime import datetime
from pod_discover.config import RecommendationWeights
from pod_discover.models import Episode


def calculate_trending_score(feed_id: int, trending_data: dict[int, dict]) -> float:
    """
    Score based on trending rank (0.0-1.0, higher rank = higher score).

    Uses logarithmic decay:
    - rank 0-10: 1.0-0.8
    - rank 11-30: 0.8-0.5
    - rank 31+: <0.5

    Args:
        feed_id: The podcast feed ID to score
        trending_data: Dict mapping feed_id -> {"rank": int, ...}

    Returns:
        Score between 0.0 and 1.0
    """
    if not trending_data or feed_id not in trending_data:
        return 0.0

    rank = trending_data[feed_id].get("rank", None)
    if rank is None:
        return 0.0

    # Logarithmic decay tuned for desired ranges
    # rank 1: ~0.95+, rank 10: ~0.8, rank 30: ~0.5, rank 100: ~0.2
    # Use exponential decay with rank
    # e^(-k*rank) where k is chosen to match desired ranges
    # k = 0.025 gives: rank 1: 0.975, rank 10: 0.778, rank 30: 0.472
    score = math.exp(-0.025 * rank)

    return max(0.0, min(1.0, score))


def calculate_social_score(podcast_name: str, reddit_mentions: dict[str, int]) -> float:
    """
    Score based on Reddit mentions (0.0-1.0, more mentions = higher score).

    Uses logarithmic scaling:
    - 10+ mentions: 1.0
    - 5-9 mentions: 0.7-0.9
    - 1-4 mentions: 0.3-0.6
    - 0 mentions: 0.0

    Args:
        podcast_name: Name of the podcast (case-sensitive)
        reddit_mentions: Dict mapping podcast name -> mention count

    Returns:
        Score between 0.0 and 1.0
    """
    if not reddit_mentions or podcast_name not in reddit_mentions:
        return 0.0

    mentions = reddit_mentions[podcast_name]
    if mentions == 0:
        return 0.0

    # Piecewise linear scaling to match spec ranges exactly
    if mentions >= 10:
        return 1.0
    elif mentions >= 5:
        # 5-9 mentions: 0.7-0.9
        # Linear interpolation: 0.7 at 5, 0.9 at 9
        return 0.7 + (mentions - 5) * (0.9 - 0.7) / (9 - 5)
    else:
        # 1-4 mentions: 0.3-0.6
        # Linear interpolation: 0.3 at 1, 0.6 at 4
        return 0.3 + (mentions - 1) * (0.6 - 0.3) / (4 - 1)


def calculate_popularity_score(episode: Episode) -> float:
    """
    Score based on popularity indicators (0.0-1.0).

    This is a placeholder implementation. In the future, this could use:
    - Podcast Index popularity metrics
    - Subscriber counts
    - Historical listen data

    Args:
        episode: Episode to score

    Returns:
        Currently returns 0.5 as a neutral placeholder
    """
    # Placeholder: return neutral score
    return 0.5


def calculate_recency_score(episode: Episode) -> float:
    """
    Score based on publish date (0.0-1.0, recent = higher).

    Uses exponential decay from publish date:
    - <1 day: 1.0
    - <7 days: 0.8-1.0
    - <30 days: 0.5-0.8
    - 30+ days: <0.5

    Args:
        episode: Episode with date_published field

    Returns:
        Score between 0.0 and 1.0
    """
    if not episode.date_published:
        return 0.0

    try:
        # Parse ISO format date
        from datetime import timezone

        pub_date_str = episode.date_published.replace('Z', '+00:00')
        pub_date = datetime.fromisoformat(pub_date_str)

        # Ensure both datetimes are timezone-aware for comparison
        if pub_date.tzinfo is None:
            # If naive, assume UTC
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        # Calculate age in days
        age_seconds = (now - pub_date).total_seconds()
        age_days = age_seconds / 86400.0

        # Exponential decay tuned for desired ranges
        # Need 7 days >= 0.8, so use longer half-life
        # With half_life = 25: 1 day: ~0.97, 7 days: ~0.81, 14 days: ~0.66, 30 days: ~0.43
        half_life = 25.0
        score = math.exp(-age_days * math.log(2) / half_life)

        return max(0.0, min(1.0, score))

    except (ValueError, AttributeError):
        # Invalid date format
        return 0.0


def calculate_duration_match(episode: Episode, preferred_duration_minutes: int = 30) -> float:
    """
    Score based on duration match (0.0-1.0, closer to preferred = higher).

    Uses Gaussian curve centered on preferred duration:
    - Exact match: 1.0
    - Within 10 min: 0.8-1.0
    - Within 30 min: 0.5-0.8
    - 30+ min off: <0.5

    Args:
        episode: Episode with duration_seconds field
        preferred_duration_minutes: User's preferred episode length in minutes

    Returns:
        Score between 0.0 and 1.0
    """
    if episode.duration_seconds is None:
        return 0.0

    duration_minutes = episode.duration_seconds / 60.0

    # Gaussian curve: e^(-(diff^2) / (2 * sigma^2))
    # Need 30 min difference >= 0.5, so use wider sigma
    # With sigma = 25: 10 min: ~0.84, 20 min: ~0.61, 30 min: ~0.43
    # Need to scale up slightly - use sigma = 27 to get 30 min closer to 0.5
    diff = abs(duration_minutes - preferred_duration_minutes)
    sigma = 27.0
    score = math.exp(-(diff ** 2) / (2 * sigma ** 2))

    return max(0.0, min(1.0, score))


def calculate_composite_score(
    episode: Episode,
    trending_score: float,
    social_score: float,
    popularity_score: float,
    recency_score: float,
    duration_score: float,
    ai_score: float,
    weights: type[RecommendationWeights] = RecommendationWeights,
) -> float:
    """
    Weighted combination of all scores.

    Combines individual scores using the weights defined in config.py.
    The weights sum to 1.0, so the result is also in the range 0.0-1.0.

    Args:
        episode: Episode being scored (not used in calculation, for API consistency)
        trending_score: Score from calculate_trending_score
        social_score: Score from calculate_social_score
        popularity_score: Score from calculate_popularity_score
        recency_score: Score from calculate_recency_score
        duration_score: Score from calculate_duration_match
        ai_score: Score from AI taste matching (external)
        weights: RecommendationWeights class with weight constants

    Returns:
        Composite score between 0.0 and 1.0
    """
    composite = (
        trending_score * weights.TRENDING +
        social_score * weights.SOCIAL_BUZZ +
        popularity_score * weights.POPULARITY +
        recency_score * weights.RECENCY +
        duration_score * weights.DURATION_MATCH +
        ai_score * weights.AI_MATCH
    )

    return max(0.0, min(1.0, composite))
