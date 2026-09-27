import pytest

from app.models.enums import FindingStatus, Severity
from app.services.diff_compare import (
    DiffBucket,
    FindingSnapshot,
    classify_finding_pair,
    compare_failed_metrics,
)


def _snap(
    status: FindingStatus,
    severity: Severity,
    risk_score: int,
) -> FindingSnapshot:
    return FindingSnapshot(status=status, severity=severity, risk_score=risk_score)


def test_passed_to_failed_is_new_issue() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.PASSED, Severity.LOW, 80),
        _snap(FindingStatus.FAILED, Severity.HIGH, 40),
    )
    assert result == DiffBucket.NEW_ISSUES


def test_missing_base_failed_head_is_new_issue() -> None:
    result = classify_finding_pair(
        None,
        _snap(FindingStatus.FAILED, Severity.HIGH, 30),
    )
    assert result == DiffBucket.NEW_ISSUES


def test_failed_to_passed_is_solved() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.FAILED, Severity.HIGH, 40),
        _snap(FindingStatus.PASSED, Severity.LOW, 90),
    )
    assert result == DiffBucket.SOLVED_ISSUES


def test_failed_high_to_critical_is_worsened() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.FAILED, Severity.HIGH, 40),
        _snap(FindingStatus.FAILED, Severity.CRITICAL, 30),
    )
    assert result == DiffBucket.WORSENED_ISSUES


def test_failed_critical_to_high_is_improved() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.FAILED, Severity.CRITICAL, 90),
        _snap(FindingStatus.FAILED, Severity.HIGH, 20),
    )
    assert result == DiffBucket.IMPROVED_ISSUES


def test_same_severity_lower_risk_score_is_worsened() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.FAILED, Severity.HIGH, 70),
        _snap(FindingStatus.FAILED, Severity.HIGH, 50),
    )
    assert result == DiffBucket.WORSENED_ISSUES


def test_same_severity_higher_risk_score_is_improved() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.FAILED, Severity.HIGH, 50),
        _snap(FindingStatus.FAILED, Severity.HIGH, 70),
    )
    assert result == DiffBucket.IMPROVED_ISSUES


def test_same_severity_same_risk_is_unchanged() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.FAILED, Severity.MEDIUM, 40),
        _snap(FindingStatus.FAILED, Severity.MEDIUM, 40),
    )
    assert result == DiffBucket.UNCHANGED


def test_passed_to_passed_is_unchanged() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.PASSED, Severity.LOW, 90),
        _snap(FindingStatus.PASSED, Severity.LOW, 95),
    )
    assert result == DiffBucket.UNCHANGED


def test_exists_only_in_base_is_missing_in_head() -> None:
    result = classify_finding_pair(
        _snap(FindingStatus.FAILED, Severity.HIGH, 30),
        None,
    )
    assert result == DiffBucket.MISSING_IN_HEAD


def test_missing_base_passed_head_is_newly_added_passed() -> None:
    result = classify_finding_pair(
        None,
        _snap(FindingStatus.PASSED, Severity.LOW, 90),
    )
    assert result == DiffBucket.NEWLY_ADDED_PASSED


def test_severity_worsens_even_if_risk_score_improves() -> None:
    """Severity precedence: High->Critical is worsened despite risk 30->90."""
    result = compare_failed_metrics(
        _snap(FindingStatus.FAILED, Severity.HIGH, 30),
        _snap(FindingStatus.FAILED, Severity.CRITICAL, 90),
    )
    assert result == DiffBucket.WORSENED_ISSUES


def test_severity_improves_even_if_risk_score_worsens() -> None:
    """Severity precedence: Critical->High is improved despite risk 90->20."""
    result = compare_failed_metrics(
        _snap(FindingStatus.FAILED, Severity.CRITICAL, 90),
        _snap(FindingStatus.FAILED, Severity.HIGH, 20),
    )
    assert result == DiffBucket.IMPROVED_ISSUES


def test_classify_requires_at_least_one_side() -> None:
    with pytest.raises(ValueError):
        classify_finding_pair(None, None)
