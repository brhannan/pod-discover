# src/pod_discover/config.py
"""
Recommendation System Configuration

SCORING WEIGHTS:
These weights control how different signals influence recommendations.
Total must sum to 1.0 (100%).

Personalization signals (target: 70%):
- AI_MATCH: Core taste matching from Claude analysis
- DURATION_MATCH: How well episode length fits user preference
- RECENCY: Preference for newer content

Discovery signals (target: 30%):
- TRENDING: What's currently popular on Podcast Index
- SOCIAL_BUZZ: Reddit community mentions
- POPULARITY: Established show quality proxy
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
            cls.AI_MATCH,
            cls.DURATION_MATCH,
            cls.RECENCY,
            cls.TRENDING,
            cls.SOCIAL_BUZZ,
            cls.POPULARITY,
        ])
        if abs(total - 1.0) >= 0.001:
            raise AssertionError(f"Weights must sum to 1.0, got {total}")
        return True


# Validate on import
RecommendationWeights.validate()


# Cache TTLs (in seconds)
TRENDING_CACHE_TTL = 4 * 60 * 60  # 4 hours
REDDIT_CACHE_TTL = 6 * 60 * 60  # 6 hours
REC_CACHE_TTL = 1 * 60 * 60  # 1 hour

# Reddit subreddits to monitor
REDDIT_SUBREDDITS = [
    "podcasts",
    "TrueCrimePodcasts",
]
