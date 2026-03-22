"""Tests for race time predictions."""

from forma.domain.race_predictor import predict_race_times


def test_predicts_all_four_distances():
    results = predict_race_times(5000, 25 * 60)

    assert len(results) == 4


def test_5k_prediction_from_5k_is_close_to_input():
    results = predict_race_times(5000, 25 * 60)
    five_k = next(r for r in results if r["distance_label"] == "5 km")

    assert abs(five_k["predicted_seconds"] - 25 * 60) < 5


def test_10k_slower_than_5k():
    results = predict_race_times(5000, 25 * 60)
    five_k = next(r for r in results if r["distance_label"] == "5 km")
    ten_k = next(r for r in results if r["distance_label"] == "10 km")

    assert ten_k["predicted_seconds"] > five_k["predicted_seconds"]


def test_marathon_from_10k():
    # 50 min 10k → roughly 3:40-3:50 marathon
    results = predict_race_times(10000, 50 * 60)
    marathon = next(r for r in results if r["distance_label"] == "Marathon")

    assert 3 * 3600 + 30 * 60 < marathon["predicted_seconds"] < 4 * 3600


def test_returns_empty_for_invalid_input():
    assert predict_race_times(0, 100) == []
    assert predict_race_times(5000, 0) == []


def test_predicted_time_format():
    results = predict_race_times(5000, 25 * 60)
    five_k = next(r for r in results if r["distance_label"] == "5 km")

    assert ":" in five_k["predicted_time"]
    assert "/km" in five_k["predicted_pace"]
