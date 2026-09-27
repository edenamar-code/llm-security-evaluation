from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Finding, Run, TestCase

EXPECTED_AVERAGE = (90 + 40 + 27) / 3


def test_ingest_valid_run_returns_201(client, sample_payload: dict) -> None:
    response = client.post("/runs", json=sample_payload)
    assert response.status_code == 201

    body = response.json()
    assert body["run_id"] == "run_001"
    assert body["model_version"] == "model-v1"
    assert body["summary"]["total_findings"] == 3
    assert body["summary"]["critical_count"] == 1
    assert body["summary"]["high_count"] == 1
    assert body["summary"]["medium_count"] == 1
    assert body["summary"]["low_count"] == 0
    assert body["summary"]["average_risk_score"] == EXPECTED_AVERAGE


def test_ingest_persists_run_findings_and_test_cases(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    response = client.post("/runs", json=sample_payload)
    assert response.status_code == 201

    assert db.scalar(select(func.count()).select_from(Run)) == 1
    assert db.scalar(select(func.count()).select_from(Finding)) == 3
    assert db.scalar(select(func.count()).select_from(TestCase)) == 3

    run = db.scalar(select(Run).where(Run.run_id == "run_001"))
    assert run is not None
    assert run.total_findings == 3
    assert run.critical_count == 1
    assert run.high_count == 1
    assert run.medium_count == 1
    assert run.low_count == 0
    assert run.average_risk_score == EXPECTED_AVERAGE


def test_get_run_returns_persisted_summary(client, sample_payload: dict) -> None:
    client.post("/runs", json=sample_payload)
    response = client.get("/runs/run_001")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_findings"] == 3
    assert body["summary"]["critical_count"] == 1


def test_get_run_not_found(client) -> None:
    response = client.get("/runs/missing")
    assert response.status_code == 404


def test_duplicate_run_id_returns_409(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    first = client.post("/runs", json=sample_payload)
    assert first.status_code == 201

    second = client.post("/runs", json=sample_payload)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]

    assert db.scalar(select(func.count()).select_from(Run)) == 1
    assert db.scalar(select(func.count()).select_from(Finding)) == 3
    assert db.scalar(select(func.count()).select_from(TestCase)) == 3


def test_same_test_case_reused_across_runs(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    first = client.post("/runs", json=sample_payload)
    assert first.status_code == 201

    second_payload = {
        **sample_payload,
        "run_id": "run_002",
        "model_version": "model-v2",
        "timestamp": "2026-09-28T10:00:00Z",
        "findings": [sample_payload["findings"][0]],
    }
    second = client.post("/runs", json=second_payload)
    assert second.status_code == 201

    assert db.scalar(select(func.count()).select_from(TestCase)) == 3
    assert db.scalar(select(func.count()).select_from(Run)) == 2
    assert db.scalar(select(func.count()).select_from(Finding)) == 4

    test_case = db.scalar(select(TestCase).where(TestCase.test_case_id == "JB-001"))
    assert test_case is not None
    assert len(test_case.findings) == 2


def test_duplicate_test_case_id_in_payload_rejected(
    client,
    sample_payload: dict,
) -> None:
    payload = {
        **sample_payload,
        "findings": [
            sample_payload["findings"][0],
            {**sample_payload["findings"][0], "actual_output": "another"},
        ],
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_invalid_risk_score_rejected(client, sample_payload: dict) -> None:
    payload = {
        **sample_payload,
        "findings": [{**sample_payload["findings"][0], "risk_score": 150}],
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_invalid_severity_rejected(client, sample_payload: dict) -> None:
    payload = {
        **sample_payload,
        "findings": [{**sample_payload["findings"][0], "severity": "Extreme"}],
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_invalid_status_rejected(client, sample_payload: dict) -> None:
    payload = {
        **sample_payload,
        "findings": [{**sample_payload["findings"][0], "status": "pending"}],
    }
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_conflicting_test_case_definition_rejected(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    db.add(
        TestCase(
            test_case_id="JB-001",
            category="Jailbreak",
            sub_category="DAN",
            prompt="ORIGINAL PROMPT",
        )
    )
    db.commit()

    response = client.post("/runs", json=sample_payload)
    assert response.status_code == 409
    assert "different category, sub_category, or prompt" in response.json()["detail"]


def test_ingestion_failure_rolls_back_entire_transaction(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    """A conflict mid-payload must not leave a partial Run or new TestCases."""
    db.add(
        TestCase(
            test_case_id="PI-001",
            category="Prompt Injection",
            sub_category="Direct",
            prompt="DIFFERENT PROMPT THAT CONFLICTS",
        )
    )
    db.commit()

    response = client.post("/runs", json=sample_payload)
    assert response.status_code == 409

    assert db.scalar(select(func.count()).select_from(Run)) == 0
    assert db.scalar(select(func.count()).select_from(Finding)) == 0
    # Only the pre-seeded conflicting TestCase remains; JB-001 / DL-001 rolled back.
    assert db.scalar(select(func.count()).select_from(TestCase)) == 1
    remaining = db.scalar(select(TestCase).where(TestCase.test_case_id == "PI-001"))
    assert remaining is not None
    assert remaining.prompt == "DIFFERENT PROMPT THAT CONFLICTS"
    assert db.scalar(select(TestCase).where(TestCase.test_case_id == "JB-001")) is None
