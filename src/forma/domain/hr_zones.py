"""Heart rate zone calculation — matches the JS _computeZones logic."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ZoneBounds:
    """BPM boundaries for a single HR zone (inclusive lower, exclusive upper)."""
    lower: float
    upper: float


def compute_zone2_bounds(max_hr: int, aerobic_threshold_bpm: int | None = None) -> ZoneBounds:
    """Return the Zone 2 BPM range for the given athlete config.

    Two modes:
    - Calibrated: when aerobic_threshold_bpm is set, Z2 = [vt1 - 15, vt1)
    - Percentage: fallback, Z2 = [60%, 70%) of max HR
    """
    if aerobic_threshold_bpm and aerobic_threshold_bpm < max_hr:
        return ZoneBounds(
            lower=aerobic_threshold_bpm - 15,
            upper=float(aerobic_threshold_bpm),
        )
    return ZoneBounds(
        lower=max_hr * 0.60,
        upper=max_hr * 0.70,
    )
