from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Finding, FindingStatus, Run, TestCase
from app.schemas.stability import (
    StabilityHistoryItemOut,
    StabilityReportOut,
)
from app.services.stability_calc import calculate_stability


class StabilityNotFoundError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _load_recent_findings(
    db: Session,
    *,
    test_case_db_id: int,
    n: int,
) -> list[Finding]:
    """Fetch the latest N findings for a TestCase ordered by run time.

    ORDER BY and LIMIT run in the database (newest first). Results are
    reversed to chronological order for transition calculation.

    Assumption: when Run.timestamp values are equal, Run.id DESC is the
    secondary sort so ordering stays deterministic.
    """
    rows = (
        db.scalars(
            select(Finding)
            .where(Finding.test_case_db_id == test_case_db_id)
            .options(joinedload(Finding.run))
            .join(Run, Finding.run_db_id == Run.id)
            .order_by(Run.timestamp.desc(), Run.id.desc())
            .limit(n)
        )
        .unique()
        .all()
    )
    return list(reversed(rows))


def get_test_case_stability(
    db: Session,
    *,
    test_case_id: str,
    n: int,
) -> StabilityReportOut:
    test_case = db.scalar(
        select(TestCase).where(TestCase.test_case_id == test_case_id)
    )
    if test_case is None:
        raise StabilityNotFoundError(
            f"TestCase with test_case_id '{test_case_id}' not found"
        )

    findings = _load_recent_findings(db, test_case_db_id=test_case.id, n=n)
    statuses: list[FindingStatus] = [finding.status for finding in findings]
    metrics = calculate_stability(statuses)

    history = [
        StabilityHistoryItemOut(
            run_id=finding.run.run_id,
            model_version=finding.run.model_version,
            timestamp=finding.run.timestamp,
            status=finding.status,
        )
        for finding in findings
    ]

    message: str | None = None
    if metrics.stability_score is None:
        message = "At least 2 observations are required to calculate stability."

    return StabilityReportOut(
        test_case_id=test_case_id,
        requested_runs=n,
        observations=metrics.observations,
        transitions=metrics.transitions,
        stability_score=metrics.stability_score,
        pass_rate=metrics.pass_rate,
        message=message,
        history=history,
    )
