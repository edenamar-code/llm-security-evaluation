from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Finding, Run, Severity, TestCase
from app.schemas.runs import FindingCreate, RunCreate


class IngestionConflictError(Exception):
    """Raised when ingestion conflicts with existing data (HTTP 409)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _calculate_summary(findings: list[FindingCreate]) -> dict[str, int | float]:
    total = len(findings)
    if total == 0:
        return {
            "total_findings": 0,
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "average_risk_score": 0.0,
        }

    return {
        "total_findings": total,
        "critical_count": sum(1 for f in findings if f.severity == Severity.CRITICAL),
        "high_count": sum(1 for f in findings if f.severity == Severity.HIGH),
        "medium_count": sum(1 for f in findings if f.severity == Severity.MEDIUM),
        "low_count": sum(1 for f in findings if f.severity == Severity.LOW),
        "average_risk_score": sum(f.risk_score for f in findings) / total,
    }


def _get_or_create_test_case(db: Session, finding: FindingCreate) -> TestCase:
    existing = db.scalar(
        select(TestCase).where(TestCase.test_case_id == finding.test_case_id)
    )
    if existing is None:
        test_case = TestCase(
            test_case_id=finding.test_case_id,
            category=finding.category,
            sub_category=finding.sub_category,
            prompt=finding.prompt,
        )
        db.add(test_case)
        db.flush()
        return test_case

    if (
        existing.category != finding.category
        or existing.sub_category != finding.sub_category
        or existing.prompt != finding.prompt
    ):
        raise IngestionConflictError(
            f"TestCase with test_case_id '{finding.test_case_id}' already exists "
            "with a different category, sub_category, or prompt"
        )
    return existing


def ingest_run(db: Session, payload: RunCreate) -> Run:
    """Persist a full evaluation run atomically.

    Commits on success. Rolls back and re-raises on any failure so the
    request leaves no partial Run / Finding / TestCase rows.
    """
    try:
        existing_run = db.scalar(select(Run).where(Run.run_id == payload.run_id))
        if existing_run is not None:
            raise IngestionConflictError(
                f"Run with run_id '{payload.run_id}' already exists"
            )

        summary = _calculate_summary(payload.findings)
        run = Run(
            run_id=payload.run_id,
            model_version=payload.model_version,
            timestamp=payload.timestamp,
            total_findings=int(summary["total_findings"]),
            critical_count=int(summary["critical_count"]),
            high_count=int(summary["high_count"]),
            medium_count=int(summary["medium_count"]),
            low_count=int(summary["low_count"]),
            average_risk_score=float(summary["average_risk_score"]),
        )
        db.add(run)
        db.flush()

        for finding_in in payload.findings:
            test_case = _get_or_create_test_case(db, finding_in)
            db.add(
                Finding(
                    run_db_id=run.id,
                    test_case_db_id=test_case.id,
                    actual_output=finding_in.actual_output,
                    severity=finding_in.severity,
                    risk_score=finding_in.risk_score,
                    status=finding_in.status,
                )
            )

        db.commit()
        db.refresh(run)
        return run
    except Exception:
        db.rollback()
        raise


def get_run_by_external_id(db: Session, run_id: str) -> Run | None:
    return db.scalar(select(Run).where(Run.run_id == run_id))
