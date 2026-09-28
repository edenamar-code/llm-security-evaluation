from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Finding, Run
from app.schemas.diff import (
    DiffItem,
    DiffReport,
    DiffSummary,
    FindingSide,
)
from app.services.diff_compare import (
    DiffBucket,
    FindingSnapshot,
    classify_finding_pair,
)


class DiffNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class DiffValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _load_run_with_findings(db: Session, run_id: str) -> Run | None:
    """Load a run and all findings+test_cases in two SQL queries (selectinload)."""
    return db.scalar(
        select(Run)
        .where(Run.run_id == run_id)
        .options(selectinload(Run.findings).selectinload(Finding.test_case))
    )


def _finding_map(run: Run) -> dict[str, Finding]:
    return {finding.test_case.test_case_id: finding for finding in run.findings}


def _to_snapshot(finding: Finding) -> FindingSnapshot:
    return FindingSnapshot(
        status=finding.status,
        severity=finding.severity,
        risk_score=finding.risk_score,
    )


def _to_side(finding: Finding | None) -> FindingSide | None:
    if finding is None:
        return None
    return FindingSide(
        status=finding.status,
        severity=finding.severity,
        risk_score=finding.risk_score,
    )


def _build_item(
    test_case_id: str,
    base_finding: Finding | None,
    head_finding: Finding | None,
) -> DiffItem:
    source = head_finding or base_finding
    assert source is not None
    return DiffItem(
        test_case_id=test_case_id,
        category=source.test_case.category,
        sub_category=source.test_case.sub_category,
        base=_to_side(base_finding),
        head=_to_side(head_finding),
    )


def compare_runs(db: Session, base_run_id: str, head_run_id: str) -> DiffReport:
    """Compare two runs by test_case_id in O(n + m) time."""
    if base_run_id == head_run_id:
        raise DiffValidationError("base_run_id and head_run_id must be different")

    base_run = _load_run_with_findings(db, base_run_id)
    if base_run is None:
        raise DiffNotFoundError(f"Run with run_id '{base_run_id}' not found")

    head_run = _load_run_with_findings(db, head_run_id)
    if head_run is None:
        raise DiffNotFoundError(f"Run with run_id '{head_run_id}' not found")

    base_map = _finding_map(base_run)
    head_map = _finding_map(head_run)
    all_ids = set(base_map) | set(head_map)

    buckets: dict[DiffBucket, list[DiffItem]] = {bucket: [] for bucket in DiffBucket}

    for test_case_id in sorted(all_ids):
        base_finding = base_map.get(test_case_id)
        head_finding = head_map.get(test_case_id)
        base_snap = _to_snapshot(base_finding) if base_finding else None
        head_snap = _to_snapshot(head_finding) if head_finding else None
        bucket = classify_finding_pair(base_snap, head_snap)
        buckets[bucket].append(_build_item(test_case_id, base_finding, head_finding))

    summary = DiffSummary(
        new_issues=len(buckets[DiffBucket.NEW_ISSUES]),
        solved_issues=len(buckets[DiffBucket.SOLVED_ISSUES]),
        worsened_issues=len(buckets[DiffBucket.WORSENED_ISSUES]),
        improved_issues=len(buckets[DiffBucket.IMPROVED_ISSUES]),
        unchanged=len(buckets[DiffBucket.UNCHANGED]),
        missing_in_head=len(buckets[DiffBucket.MISSING_IN_HEAD]),
        newly_added_passed=len(buckets[DiffBucket.NEWLY_ADDED_PASSED]),
    )

    return DiffReport(
        base_run_id=base_run_id,
        head_run_id=head_run_id,
        summary=summary,
        new_issues=buckets[DiffBucket.NEW_ISSUES],
        solved_issues=buckets[DiffBucket.SOLVED_ISSUES],
        worsened_issues=buckets[DiffBucket.WORSENED_ISSUES],
        improved_issues=buckets[DiffBucket.IMPROVED_ISSUES],
        unchanged=buckets[DiffBucket.UNCHANGED],
        missing_in_head=buckets[DiffBucket.MISSING_IN_HEAD],
        newly_added_passed=buckets[DiffBucket.NEWLY_ADDED_PASSED],
    )
