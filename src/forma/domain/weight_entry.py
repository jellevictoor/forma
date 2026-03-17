"""Weight entry domain entity."""

from datetime import date

from pydantic import BaseModel


class WeightEntry(BaseModel):
    """A single weight measurement for an athlete."""

    id: str
    athlete_id: str
    weight_kg: float
    recorded_at: date
    notes: str = ""
