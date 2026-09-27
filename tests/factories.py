"""Test helpers for building payloads and ORM objects without external factories."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Finding, FindingStatus, Run, Severity, TestCase


def make_finding_payload(
    *,
    test_case_id: str = "TC-001",
    category: str = "Jailbreak",
    sub_category: str = "DAN",
    prompt: str = "Example prompt",
    actual_output: str = "Example output",
    severity: str = "High",
    risk_score: int = 40,
    status: str = "failed",
) -> dict[str, Any]:
    return {
        "test_case_id": test_case_id,
        "category": category,
        "sub_category": sub_category,
        "prompt": prompt,
        "actual_output": actual_output,
        "severity": severity,
        "risk_score": risk_score,
        "status": status,
    }


def make_run_payload(
    *,
    run_id: str = "run_001",
    model_version: str = "model-v1",
    timestamp: str = "2026-09-27T10:00:00Z",
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if findings is None:
        findings = [make_finding_payload()]
    return {
        "run_id": run_id,
        "model_version": model_version,
        "timestamp": timestamp,
        "findings": findings,
    }


def persist_run(
    db: Session,
    *,
    run_id: str = "run-001",
    model_version: str = "v1",
    timestamp: datetime | None = None,
) -> Run:
    run = Run(
        run_id=run_id,
        model_version=model_version,
        timestamp=timestamp or datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def persist_test_case(
    db: Session,
    *,
    test_case_id: str = "tc-001",
    category: str = "Jailbreak",
    sub_category: str = "DAN",
    prompt: str = "Example prompt",
) -> TestCase:
    test_case = TestCase(
        test_case_id=test_case_id,
        category=category,
        sub_category=sub_category,
        prompt=prompt,
    )
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case


def persist_finding(
    db: Session,
    *,
    run: Run,
    test_case: TestCase,
    actual_output: str = "output",
    severity: Severity = Severity.HIGH,
    risk_score: int = 40,
    status: FindingStatus = FindingStatus.FAILED,
) -> Finding:
    finding = Finding(
        run_db_id=run.id,
        test_case_db_id=test_case.id,
        actual_output=actual_output,
        severity=severity,
        risk_score=risk_score,
        status=status,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding
