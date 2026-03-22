"""Tests for readiness score computation."""

from forma.domain.readiness import compute_readiness


def test_positive_form_gives_high_readiness():
    score = compute_readiness(fitness=40, fatigue=25, form=15)

    assert score >= 60


def test_negative_form_gives_lower_readiness():
    score = compute_readiness(fitness=40, fatigue=50, form=-10)

    assert score < 50


def test_zero_fitness_gives_low_readiness():
    score = compute_readiness(fitness=0, fatigue=0, form=0)

    assert score <= 50


def test_score_clamped_to_100():
    score = compute_readiness(fitness=100, fatigue=10, form=90)

    assert score <= 100


def test_score_clamped_to_0():
    score = compute_readiness(fitness=5, fatigue=80, form=-75)

    assert score >= 0


def test_fresh_and_fit_is_higher_than_fresh_and_unfit():
    fit = compute_readiness(fitness=60, fatigue=30, form=30)
    unfit = compute_readiness(fitness=10, fatigue=5, form=5)

    assert fit > unfit
