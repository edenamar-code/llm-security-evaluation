from enum import Enum
from typing import NamedTuple

from app.models.enums import FindingStatus, Severity

SEVERITY_RANK: dict[Severity, int] = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class DiffBucket(str, Enum):
    NEW_ISSUES = "new_issues"
    SOLVED_ISSUES = "solved_issues"
    WORSENED_ISSUES = "worsened_issues"
    IMPROVED_ISSUES = "improved_issues"
    UNCHANGED = "unchanged"
    MISSING_IN_HEAD = "missing_in_head"
    NEWLY_ADDED_PASSED = "newly_added_passed"


class FindingSnapshot(NamedTuple):
    """DB-free finding view used by pure comparison helpers."""

    status: FindingStatus
    severity: Severity
    risk_score: int


def compare_failed_metrics(
    base: FindingSnapshot,
    head: FindingSnapshot,
) -> DiffBucket:
    """Compare two failed findings.

    Severity takes precedence over risk_score.

    Assignment risk_score convention:
    - lower risk_score  => worse
    - higher risk_score => better
    """
    base_rank = SEVERITY_RANK[base.severity]
    head_rank = SEVERITY_RANK[head.severity]

    if head_rank > base_rank:
        return DiffBucket.WORSENED_ISSUES
    if head_rank < base_rank:
        return DiffBucket.IMPROVED_ISSUES

    # Same severity: risk_score decides (inverted vs typical risk naming).
    if head.risk_score < base.risk_score:
        return DiffBucket.WORSENED_ISSUES
    if head.risk_score > base.risk_score:
        return DiffBucket.IMPROVED_ISSUES
    return DiffBucket.UNCHANGED


def classify_finding_pair(
    base: FindingSnapshot | None,
    head: FindingSnapshot | None,
) -> DiffBucket:
    """Classify one test_case_id transition between base and head runs."""
    if base is None and head is None:
        raise ValueError("At least one side of the comparison must be present")

    if base is None:
        assert head is not None
        if head.status == FindingStatus.FAILED:
            return DiffBucket.NEW_ISSUES
        return DiffBucket.NEWLY_ADDED_PASSED

    if head is None:
        return DiffBucket.MISSING_IN_HEAD

    # Both present
    if base.status == FindingStatus.PASSED and head.status == FindingStatus.FAILED:
        return DiffBucket.NEW_ISSUES

    if base.status == FindingStatus.FAILED and head.status == FindingStatus.PASSED:
        return DiffBucket.SOLVED_ISSUES

    if base.status == FindingStatus.PASSED and head.status == FindingStatus.PASSED:
        return DiffBucket.UNCHANGED

    # failed -> failed
    return compare_failed_metrics(base, head)
