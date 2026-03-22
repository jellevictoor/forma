"""Tests for recovery time estimation."""

from forma.domain.recovery import estimate_recovery_hours, recovery_label


def test_short_easy_workout_needs_little_recovery():
    hours = estimate_recovery_hours(25, average_heartrate=120, max_heartrate=185, form=5)

    assert hours <= 12


def test_long_hard_workout_needs_more_recovery():
    hours = estimate_recovery_hours(90, average_heartrate=165, max_heartrate=185, form=-10)

    assert hours >= 48


def test_fatigued_athlete_needs_longer_recovery():
    fresh = estimate_recovery_hours(60, average_heartrate=140, max_heartrate=185, form=15)
    tired = estimate_recovery_hours(60, average_heartrate=140, max_heartrate=185, form=-20)

    assert tired > fresh


def test_no_hr_data_uses_duration_only():
    hours = estimate_recovery_hours(45, average_heartrate=None, max_heartrate=None, form=0)

    assert 12 <= hours <= 36


def test_recovery_label_short():
    assert "Ready" in recovery_label(10)


def test_recovery_label_long():
    assert "rest day" in recovery_label(48)
