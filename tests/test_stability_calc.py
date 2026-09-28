"""Pure unit tests for stability calculation (no DB / FastAPI)."""

from app.models.enums import FindingStatus
from app.services.stability_calc import calculate_stability


def test_all_passed() -> None:
    metrics = calculate_stability(
        [FindingStatus.PASSED, FindingStatus.PASSED, FindingStatus.PASSED]
    )
    assert metrics.transitions == 0
    assert metrics.observations == 3
    assert metrics.stability_score == 100.0


def test_all_failed() -> None:
    metrics = calculate_stability(
        [FindingStatus.FAILED, FindingStatus.FAILED, FindingStatus.FAILED]
    )
    assert metrics.transitions == 0
    assert metrics.observations == 3
    assert metrics.stability_score == 100.0


def test_alternating_passed_failed() -> None:
    metrics = calculate_stability(
        [
            FindingStatus.PASSED,
            FindingStatus.FAILED,
            FindingStatus.PASSED,
            FindingStatus.FAILED,
        ]
    )
    assert metrics.transitions == 3
    assert metrics.observations == 4
    assert metrics.stability_score == 0.0


def test_two_passed_then_two_failed() -> None:
    metrics = calculate_stability(
        [
            FindingStatus.PASSED,
            FindingStatus.PASSED,
            FindingStatus.FAILED,
            FindingStatus.FAILED,
        ]
    )
    assert metrics.transitions == 1
    assert metrics.observations == 4
    assert metrics.stability_score == 66.67


def test_exactly_two_failed_then_passed() -> None:
    metrics = calculate_stability([FindingStatus.FAILED, FindingStatus.PASSED])
    assert metrics.transitions == 1
    assert metrics.observations == 2
    assert metrics.stability_score == 0.0


def test_exactly_two_failed() -> None:
    metrics = calculate_stability([FindingStatus.FAILED, FindingStatus.FAILED])
    assert metrics.transitions == 0
    assert metrics.observations == 2
    assert metrics.stability_score == 100.0


def test_single_observation_returns_null_score() -> None:
    metrics = calculate_stability([FindingStatus.PASSED])
    assert metrics.transitions == 0
    assert metrics.observations == 1
    assert metrics.stability_score is None


def test_empty_observations_returns_null_score() -> None:
    metrics = calculate_stability([])
    assert metrics.transitions == 0
    assert metrics.observations == 0
    assert metrics.stability_score is None


def test_mixed_sequence() -> None:
    # failed, failed, passed, passed, failed -> 2 transitions of 4 possible
    metrics = calculate_stability(
        [
            FindingStatus.FAILED,
            FindingStatus.FAILED,
            FindingStatus.PASSED,
            FindingStatus.PASSED,
            FindingStatus.FAILED,
        ]
    )
    assert metrics.transitions == 2
    assert metrics.observations == 5
    assert metrics.stability_score == 50.0
