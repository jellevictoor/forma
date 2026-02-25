"""Weight entry domain entity."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class WeightEntry:
    """A single weight measurement for an athlete."""

    id: str
    athlete_id: str
    weight_kg: float
    recorded_at: date
    notes: str = field(default="")
