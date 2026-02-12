# tests/test_config.py
import pytest
from pod_discover.config import RecommendationWeights


def test_weights_sum_to_one():
    """Test that all weights sum to 1.0"""
    total = sum([
        RecommendationWeights.AI_MATCH,
        RecommendationWeights.DURATION_MATCH,
        RecommendationWeights.RECENCY,
        RecommendationWeights.TRENDING,
        RecommendationWeights.SOCIAL_BUZZ,
        RecommendationWeights.POPULARITY,
    ])
    assert abs(total - 1.0) < 0.001


def test_weights_validate_on_import():
    """Test that validate() is called and works"""
    assert RecommendationWeights.validate() is True


def test_invalid_weights_raise_error():
    """Test that weights not summing to 1.0 raise error"""
    # Temporarily break the weights
    original = RecommendationWeights.AI_MATCH
    RecommendationWeights.AI_MATCH = 0.99

    with pytest.raises(AssertionError, match="Weights must sum to 1.0"):
        RecommendationWeights.validate()

    # Restore
    RecommendationWeights.AI_MATCH = original
