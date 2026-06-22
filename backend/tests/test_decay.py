import math
from datetime import datetime, timedelta, timezone

import pytest

from app.core.decay import DecayEngine


@pytest.fixture
def engine():
    return DecayEngine()


def test_importance_decreases_over_time(engine):
    base = 0.8
    rate = 0.1
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    result = engine.calculate_current_importance(base, rate, old, access_count=0)
    expected = base * math.exp(-rate * 10)
    assert abs(result - expected) < 1e-6


def test_high_access_count_slows_decay(engine):
    base = 0.8
    rate = 0.1
    old = datetime.now(timezone.utc) - timedelta(days=10)
    low_access = engine.calculate_current_importance(base, rate, old, access_count=0)
    high_access = engine.calculate_current_importance(base, rate, old, access_count=50)
    assert high_access > low_access


def test_should_forget_below_threshold(engine):
    assert engine.should_forget(0.04) is True
    assert engine.should_forget(0.06) is False


def test_boost_importance_caps_at_1(engine):
    result = engine.boost_importance(0.95, boost=0.2)
    assert result == 1.0


def test_boost_importance_adds_correctly(engine):
    result = engine.boost_importance(0.5, boost=0.2)
    assert abs(result - 0.7) < 1e-9


def test_preferences_decay_slower_than_general(engine):
    assert engine.calculate_decay_rate_for_type("preference") < engine.calculate_decay_rate_for_type("general")


def test_pattern_decays_slower_than_bug_fix(engine):
    assert engine.calculate_decay_rate_for_type("pattern") < engine.calculate_decay_rate_for_type("bug_fix")


def test_unknown_memory_type_falls_back_to_general_rate(engine):
    assert engine.calculate_decay_rate_for_type("unknown_type") == engine.calculate_decay_rate_for_type("general")


def test_result_clamped_between_0_and_1(engine):
    # Extreme decay should never go negative
    very_old = datetime.now(timezone.utc) - timedelta(days=365)
    result = engine.calculate_current_importance(0.5, 1.0, very_old, access_count=0)
    assert 0.0 <= result <= 1.0


def test_zero_days_since_access_returns_base_importance(engine):
    now = datetime.now(timezone.utc)
    result = engine.calculate_current_importance(0.7, 0.1, now, access_count=0)
    assert abs(result - 0.7) < 1e-3


def test_naive_datetime_is_treated_as_utc(engine):
    # last_accessed without tzinfo should not raise
    naive_now = datetime.utcnow()
    result = engine.calculate_current_importance(0.7, 0.1, naive_now, access_count=0)
    assert 0.0 <= result <= 1.0
