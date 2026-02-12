# tests/test_scoring.py
import pytest
from datetime import datetime, timedelta
from pod_discover.scoring import (
    calculate_trending_score,
    calculate_social_score,
    calculate_popularity_score,
    calculate_recency_score,
    calculate_duration_match,
    calculate_composite_score,
)
from pod_discover.models import Episode
from pod_discover.config import RecommendationWeights


class TestTrendingScore:
    """Test trending score calculation based on rank"""

    def test_top_10_ranks_high_score(self):
        """Ranks 0-10 should return 0.8-1.0"""
        trending_data = {100: {"rank": 5}}
        score = calculate_trending_score(100, trending_data)
        assert 0.8 <= score <= 1.0

    def test_mid_ranks_medium_score(self):
        """Ranks 11-30 should return 0.5-0.8"""
        trending_data = {100: {"rank": 20}}
        score = calculate_trending_score(100, trending_data)
        assert 0.5 <= score <= 0.8

    def test_low_ranks_low_score(self):
        """Ranks 31+ should return <0.5"""
        trending_data = {100: {"rank": 50}}
        score = calculate_trending_score(100, trending_data)
        assert 0.0 <= score < 0.5

    def test_not_in_trending_returns_zero(self):
        """Feed not in trending data should return 0.0"""
        trending_data = {100: {"rank": 5}}
        score = calculate_trending_score(999, trending_data)
        assert score == 0.0

    def test_empty_trending_data(self):
        """Empty trending data should return 0.0"""
        score = calculate_trending_score(100, {})
        assert score == 0.0

    def test_rank_1_returns_highest_score(self):
        """Rank 1 should return maximum score"""
        trending_data = {100: {"rank": 1}}
        score = calculate_trending_score(100, trending_data)
        assert score >= 0.95  # Very close to 1.0


class TestSocialScore:
    """Test social score calculation based on Reddit mentions"""

    def test_high_mentions_high_score(self):
        """10+ mentions should return 1.0"""
        reddit_mentions = {"Test Podcast": 15}
        score = calculate_social_score("Test Podcast", reddit_mentions)
        assert score == 1.0

    def test_medium_mentions_medium_score(self):
        """5-9 mentions should return 0.7-0.9"""
        reddit_mentions = {"Test Podcast": 7}
        score = calculate_social_score("Test Podcast", reddit_mentions)
        assert 0.7 <= score <= 0.9

    def test_low_mentions_low_score(self):
        """1-4 mentions should return 0.3-0.6"""
        reddit_mentions = {"Test Podcast": 3}
        score = calculate_social_score("Test Podcast", reddit_mentions)
        assert 0.3 <= score <= 0.6

    def test_no_mentions_returns_zero(self):
        """0 mentions should return 0.0"""
        reddit_mentions = {"Test Podcast": 0}
        score = calculate_social_score("Test Podcast", reddit_mentions)
        assert score == 0.0

    def test_podcast_not_in_mentions(self):
        """Podcast not in mentions dict should return 0.0"""
        reddit_mentions = {"Other Podcast": 10}
        score = calculate_social_score("Test Podcast", reddit_mentions)
        assert score == 0.0

    def test_empty_mentions_dict(self):
        """Empty mentions dict should return 0.0"""
        score = calculate_social_score("Test Podcast", {})
        assert score == 0.0

    def test_case_sensitive_matching(self):
        """Podcast name matching should be case-sensitive"""
        reddit_mentions = {"Test Podcast": 10}
        score = calculate_social_score("test podcast", reddit_mentions)
        assert score == 0.0


class TestPopularityScore:
    """Test popularity score calculation (placeholder)"""

    def test_returns_placeholder_value(self):
        """Should return 0.5 as placeholder"""
        episode = Episode(
            id=1,
            title="Test Episode",
            description="Test description",
            feed_title="Test Podcast",
        )
        score = calculate_popularity_score(episode)
        assert score == 0.5


class TestRecencyScore:
    """Test recency score calculation based on publish date"""

    def test_very_recent_high_score(self):
        """Episodes <1 day old should return 1.0"""
        now = datetime.utcnow()
        date_str = now.isoformat()
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            date_published=date_str,
        )
        score = calculate_recency_score(episode)
        assert score >= 0.95  # Very close to 1.0

    def test_recent_week_high_score(self):
        """Episodes <7 days old should return 0.8-1.0"""
        now = datetime.utcnow()
        five_days_ago = now - timedelta(days=5)
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            date_published=five_days_ago.isoformat(),
        )
        score = calculate_recency_score(episode)
        assert 0.8 <= score <= 1.0

    def test_recent_month_medium_score(self):
        """Episodes <30 days old should return 0.5-0.8"""
        now = datetime.utcnow()
        two_weeks_ago = now - timedelta(days=14)
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            date_published=two_weeks_ago.isoformat(),
        )
        score = calculate_recency_score(episode)
        assert 0.5 <= score <= 0.8

    def test_old_episode_low_score(self):
        """Episodes 30+ days old should return <0.5"""
        now = datetime.utcnow()
        old_date = now - timedelta(days=60)
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            date_published=old_date.isoformat(),
        )
        score = calculate_recency_score(episode)
        assert 0.0 <= score < 0.5

    def test_missing_date_returns_zero(self):
        """Episode without date_published should return 0.0"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            date_published="",
        )
        score = calculate_recency_score(episode)
        assert score == 0.0

    def test_invalid_date_returns_zero(self):
        """Episode with invalid date should return 0.0"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            date_published="invalid-date",
        )
        score = calculate_recency_score(episode)
        assert score == 0.0


class TestDurationMatch:
    """Test duration matching score"""

    def test_exact_match_perfect_score(self):
        """Exact duration match should return 1.0"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            duration_seconds=30 * 60,  # 30 minutes
        )
        score = calculate_duration_match(episode, preferred_duration_minutes=30)
        assert score == 1.0

    def test_close_match_high_score(self):
        """Within 10 minutes should return 0.8-1.0"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            duration_seconds=35 * 60,  # 35 minutes
        )
        score = calculate_duration_match(episode, preferred_duration_minutes=30)
        assert 0.8 <= score <= 1.0

    def test_medium_match_medium_score(self):
        """Within 30 minutes should return 0.5-0.8"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            duration_seconds=50 * 60,  # 50 minutes
        )
        score = calculate_duration_match(episode, preferred_duration_minutes=30)
        assert 0.5 <= score <= 0.8

    def test_far_match_low_score(self):
        """30+ minutes difference should return <0.5"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            duration_seconds=90 * 60,  # 90 minutes
        )
        score = calculate_duration_match(episode, preferred_duration_minutes=30)
        assert 0.0 <= score < 0.5

    def test_missing_duration_returns_zero(self):
        """Episode without duration should return 0.0"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            duration_seconds=None,
        )
        score = calculate_duration_match(episode, preferred_duration_minutes=30)
        assert score == 0.0

    def test_default_preferred_duration(self):
        """Should use 30 minutes as default"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
            duration_seconds=30 * 60,
        )
        score = calculate_duration_match(episode)
        assert score == 1.0


class TestCompositeScore:
    """Test composite score calculation using weights"""

    def test_weighted_combination(self):
        """Should combine scores using weights"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
        )

        # All scores at 1.0 should return 1.0
        composite = calculate_composite_score(
            episode=episode,
            trending_score=1.0,
            social_score=1.0,
            popularity_score=1.0,
            recency_score=1.0,
            duration_score=1.0,
            ai_score=1.0,
            weights=RecommendationWeights,
        )
        assert abs(composite - 1.0) < 0.001

    def test_all_zeros_returns_zero(self):
        """All zero scores should return 0.0"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
        )

        composite = calculate_composite_score(
            episode=episode,
            trending_score=0.0,
            social_score=0.0,
            popularity_score=0.0,
            recency_score=0.0,
            duration_score=0.0,
            ai_score=0.0,
            weights=RecommendationWeights,
        )
        assert composite == 0.0

    def test_weights_applied_correctly(self):
        """Should apply weights correctly"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
        )

        # Only AI score at 1.0, rest at 0.0
        composite = calculate_composite_score(
            episode=episode,
            trending_score=0.0,
            social_score=0.0,
            popularity_score=0.0,
            recency_score=0.0,
            duration_score=0.0,
            ai_score=1.0,
            weights=RecommendationWeights,
        )
        expected = RecommendationWeights.AI_MATCH
        assert abs(composite - expected) < 0.001

    def test_mixed_scores(self):
        """Should handle mixed score values"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
        )

        composite = calculate_composite_score(
            episode=episode,
            trending_score=0.8,
            social_score=0.6,
            popularity_score=0.5,
            recency_score=0.9,
            duration_score=0.7,
            ai_score=0.85,
            weights=RecommendationWeights,
        )

        # Calculate expected manually
        expected = (
            0.8 * RecommendationWeights.TRENDING +
            0.6 * RecommendationWeights.SOCIAL_BUZZ +
            0.5 * RecommendationWeights.POPULARITY +
            0.9 * RecommendationWeights.RECENCY +
            0.7 * RecommendationWeights.DURATION_MATCH +
            0.85 * RecommendationWeights.AI_MATCH
        )
        assert abs(composite - expected) < 0.001

    def test_score_bounded_0_to_1(self):
        """Composite score should always be 0.0-1.0"""
        episode = Episode(
            id=1,
            title="Test",
            description="Test",
            feed_title="Test",
        )

        composite = calculate_composite_score(
            episode=episode,
            trending_score=0.5,
            social_score=0.5,
            popularity_score=0.5,
            recency_score=0.5,
            duration_score=0.5,
            ai_score=0.5,
            weights=RecommendationWeights,
        )
        assert 0.0 <= composite <= 1.0
