from dataclasses import dataclass

from app.models.enums import FindingStatus


@dataclass(frozen=True)
class StabilityMetrics:
    transitions: int
    observations: int
    stability_score: float | None


def calculate_stability(statuses: list[FindingStatus]) -> StabilityMetrics:
    """Compute stability from a chronological status sequence.

    Stability measures consistency of outcomes, not security quality:
    all-passed and all-failed are both fully stable (100).
    """
    observations = len(statuses)
    if observations < 2:
        return StabilityMetrics(
            transitions=0,
            observations=observations,
            stability_score=None,
        )

    transitions = sum(
        1 for previous, current in zip(statuses, statuses[1:]) if previous != current
    )
    possible = observations - 1
    score = round(100 * (1 - transitions / possible), 2)
    return StabilityMetrics(
        transitions=transitions,
        observations=observations,
        stability_score=score,
    )
