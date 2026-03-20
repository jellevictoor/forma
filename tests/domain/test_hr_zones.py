"""Tests for HR zone calculation."""

from forma.domain.hr_zones import ZoneBounds, compute_zone2_bounds


def test_percentage_mode_lower_bound():
    bounds = compute_zone2_bounds(max_hr=185)

    assert bounds.lower == 185 * 0.60


def test_percentage_mode_upper_bound():
    bounds = compute_zone2_bounds(max_hr=185)

    assert bounds.upper == 185 * 0.70


def test_calibrated_mode_uses_vt1():
    bounds = compute_zone2_bounds(max_hr=185, aerobic_threshold_bpm=150)

    assert bounds == ZoneBounds(lower=135, upper=150)


def test_calibrated_mode_ignored_when_vt1_exceeds_max():
    bounds = compute_zone2_bounds(max_hr=185, aerobic_threshold_bpm=200)

    assert bounds.lower == 185 * 0.60
