"""Tests for Strava client adapter."""

from forma.adapters.strava_client import STRAVA_TYPE_MAP
from forma.domain.workout import WorkoutType


def test_ebike_ride_maps_to_ebike():
    assert STRAVA_TYPE_MAP["EBikeRide"] == WorkoutType.EBIKE


def test_ride_maps_to_bike():
    assert STRAVA_TYPE_MAP["Ride"] == WorkoutType.BIKE


def test_run_maps_to_run():
    assert STRAVA_TYPE_MAP["Run"] == WorkoutType.RUN
