"""Domain tests for compute_fitness_freshness."""

from datetime import date

import pytest

from forma.domain.fitness_freshness import compute_fitness_freshness


def test_returns_list_of_dicts():
    result = compute_fitness_freshness([], display_days=7)

    assert isinstance(result, list)
    assert all(isinstance(d, dict) for d in result)


def test_form_equals_fitness_minus_fatigue():
    today = date.today()
    efforts = [{"date": today.isoformat(), "effort": 100.0}]

    result = compute_fitness_freshness(efforts, display_days=1)
    last = result[-1]

    assert last["form"] == pytest.approx(last["fitness"] - last["fatigue"], abs=0.1)


def test_empty_efforts_returns_zeros():
    result = compute_fitness_freshness([], display_days=1)
    last = result[-1]

    assert last["fitness"] == 0.0
    assert last["fatigue"] == 0.0
    assert last["form"] == 0.0


def test_display_days_limits_output_length():
    result = compute_fitness_freshness([], display_days=14)

    assert len(result) == 14
