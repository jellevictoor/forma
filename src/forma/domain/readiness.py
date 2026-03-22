"""Readiness score — single 0-100 number from fitness/fatigue/form."""


def compute_readiness(fitness: float, fatigue: float, form: float) -> int:
    """Compute a 0-100 readiness score.

    Components:
    - Form contribution (60%): TSB mapped to 0-100, centered at 50 for form=0
    - Fitness contribution (40%): higher baseline fitness = more resilient

    The score answers: "how ready am I to perform today?"
    """
    # Form: map [-30, +30] range to [0, 100], centered at 50
    form_score = max(0, min(100, 50 + form * (50 / 30)))

    # Fitness: map [0, 80] to [0, 100] — fitter athletes recover better
    fitness_score = max(0, min(100, fitness * (100 / 80)))

    # Weighted blend
    raw = form_score * 0.6 + fitness_score * 0.4

    return max(0, min(100, round(raw)))
