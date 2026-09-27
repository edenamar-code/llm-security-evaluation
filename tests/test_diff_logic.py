"""Pure unit tests for differential classification rules (no DB / FastAPI)."""

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
    assert (
        classify_finding_pair(
            _snap(FindingStatus.PASSED, Severity.LOW, 80),
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
        )
        == DiffBucket.NEW_ISSUES
    )


def test_missing_in_base_to_failed_is_new_issue() -> None:
    assert (
        classify_finding_pair(
            None,
            _snap(FindingStatus.FAILED, Severity.HIGH, 30),
        )
        == DiffBucket.NEW_ISSUES
    )


def test_failed_to_passed_is_solved_issue() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
            _snap(FindingStatus.PASSED, Severity.LOW, 90),
        )
        == DiffBucket.SOLVED_ISSUES
    )


def test_failed_high_to_critical_is_worsened() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
            _snap(FindingStatus.FAILED, Severity.CRITICAL, 30),
        )
        == DiffBucket.WORSENED_ISSUES
    )


def test_failed_medium_to_high_is_worsened() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.MEDIUM, 40),
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
        )
        == DiffBucket.WORSENED_ISSUES
    )


def test_same_severity_risk_score_decrease_is_worsened() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.HIGH, 70),
            _snap(FindingStatus.FAILED, Severity.HIGH, 50),
        )
        == DiffBucket.WORSENED_ISSUES
    )


def test_failed_critical_to_high_is_improved() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.CRITICAL, 90),
            _snap(FindingStatus.FAILED, Severity.HIGH, 20),
        )
        == DiffBucket.IMPROVED_ISSUES
    )


def test_failed_high_to_medium_is_improved() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
            _snap(FindingStatus.FAILED, Severity.MEDIUM, 40),
        )
        == DiffBucket.IMPROVED_ISSUES
    )


def test_same_severity_risk_score_increase_is_improved() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.HIGH, 50),
            _snap(FindingStatus.FAILED, Severity.HIGH, 70),
        )
        == DiffBucket.IMPROVED_ISSUES
    )


def test_passed_to_passed_is_unchanged() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.PASSED, Severity.LOW, 90),
            _snap(FindingStatus.PASSED, Severity.LOW, 95),
        )
        == DiffBucket.UNCHANGED
    )


def test_failed_same_severity_same_risk_is_unchanged() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.MEDIUM, 40),
            _snap(FindingStatus.FAILED, Severity.MEDIUM, 40),
        )
        == DiffBucket.UNCHANGED
    )


def test_exists_only_in_base_is_missing_in_head() -> None:
    assert (
        classify_finding_pair(
            _snap(FindingStatus.FAILED, Severity.HIGH, 30),
            None,
        )
        == DiffBucket.MISSING_IN_HEAD
    )


def test_missing_in_base_passed_in_head_is_newly_added_passed() -> None:
    assert (
        classify_finding_pair(
            None,
            _snap(FindingStatus.PASSED, Severity.LOW, 90),
        )
        == DiffBucket.NEWLY_ADDED_PASSED
    )


def test_severity_worsening_takes_precedence_over_risk_improvement() -> None:
    """base High/40 -> head Critical/90 must be worsened."""
    assert (
        compare_failed_metrics(
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
            _snap(FindingStatus.FAILED, Severity.CRITICAL, 90),
        )
        == DiffBucket.WORSENED_ISSUES
    )


def test_severity_improvement_takes_precedence_over_risk_worsening() -> None:
    """base Critical/90 -> head High/20 must be improved."""
    assert (
        compare_failed_metrics(
            _snap(FindingStatus.FAILED, Severity.CRITICAL, 90),
            _snap(FindingStatus.FAILED, Severity.HIGH, 20),
        )
        == DiffBucket.IMPROVED_ISSUES
    )


def test_severity_unchanged_and_risk_unchanged_is_unchanged() -> None:
    assert (
        compare_failed_metrics(
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
            _snap(FindingStatus.FAILED, Severity.HIGH, 40),
        )
        == DiffBucket.UNCHANGED
    )


def test_classify_requires_at_least_one_side() -> None:
    with pytest.raises(ValueError, match="At least one side"):
        classify_finding_pair(None, None)
