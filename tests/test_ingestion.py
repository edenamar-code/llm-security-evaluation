from copy import deepcopy

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Finding, Run, TestCase
from tests.factories import make_finding_payload, make_run_payload

EXPECTED_AVERAGE = (90 + 40 + 27) / 3


def test_valid_payload_returns_201(client, sample_payload: dict) -> None:
    response = client.post("/runs", json=sample_payload)
    assert response.status_code == 201
    body = response.json()
    assert body["run_id"] == "run_001"
    assert body["model_version"] == "model-v1"


def test_run_is_persisted(client, db: Session, sample_payload: dict) -> None:
    assert client.post("/runs", json=sample_payload).status_code == 201
    assert db.scalar(select(func.count()).select_from(Run)) == 1
    run = db.scalar(select(Run).where(Run.run_id == "run_001"))
    assert run is not None


def test_all_findings_are_persisted(client, db: Session, sample_payload: dict) -> None:
    assert client.post("/runs", json=sample_payload).status_code == 201
    assert db.scalar(select(func.count()).select_from(Finding)) == 3


def test_test_cases_are_persisted(client, db: Session, sample_payload: dict) -> None:
    assert client.post("/runs", json=sample_payload).status_code == 201
    assert db.scalar(select(func.count()).select_from(TestCase)) == 3


def test_summary_values_and_severity_counts_are_correct(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    response = client.post("/runs", json=sample_payload)
    assert response.status_code == 201
    summary = response.json()["summary"]
    assert summary["total_findings"] == 3
    assert summary["critical_count"] == 1
    assert summary["high_count"] == 1
    assert summary["medium_count"] == 1
    assert summary["low_count"] == 0
    assert summary["average_risk_score"] == EXPECTED_AVERAGE

    run = db.scalar(select(Run).where(Run.run_id == "run_001"))
    assert run is not None
    assert run.total_findings == 3
    assert run.critical_count == 1
    assert run.high_count == 1
    assert run.medium_count == 1
    assert run.low_count == 0
    assert run.average_risk_score == EXPECTED_AVERAGE


def test_average_risk_score_is_calculated_correctly(client) -> None:
    payload = make_run_payload(
        run_id="avg_run",
        findings=[
            make_finding_payload(test_case_id="A", risk_score=10, severity="Low"),
            make_finding_payload(test_case_id="B", risk_score=20, severity="Medium"),
            make_finding_payload(test_case_id="C", risk_score=30, severity="High"),
        ],
    )
    response = client.post("/runs", json=payload)
    assert response.status_code == 201
    assert response.json()["summary"]["average_risk_score"] == 20.0


def test_get_run_returns_persisted_summary(client, sample_payload: dict) -> None:
    client.post("/runs", json=sample_payload)
    response = client.get("/runs/run_001")
    assert response.status_code == 200
    assert response.json()["summary"]["total_findings"] == 3
    assert response.json()["summary"]["critical_count"] == 1


def test_get_run_not_found_returns_404(client) -> None:
    response = client.get("/runs/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Run with run_id 'missing' not found"


def test_duplicate_run_id_returns_409(client, sample_payload: dict) -> None:
    assert client.post("/runs", json=sample_payload).status_code == 201
    second = client.post("/runs", json=sample_payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "Run with run_id 'run_001' already exists"


def test_duplicate_run_id_does_not_create_duplicate_findings(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    assert client.post("/runs", json=sample_payload).status_code == 201
    assert client.post("/runs", json=sample_payload).status_code == 409
    assert db.scalar(select(func.count()).select_from(Run)) == 1
    assert db.scalar(select(func.count()).select_from(Finding)) == 3
    assert db.scalar(select(func.count()).select_from(TestCase)) == 3


def test_same_test_case_id_across_runs_reuses_one_test_case_record(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    assert client.post("/runs", json=sample_payload).status_code == 201
    second_payload = make_run_payload(
        run_id="run_002",
        model_version="model-v2",
        timestamp="2026-09-28T10:00:00Z",
        findings=[sample_payload["findings"][0]],
    )
    assert client.post("/runs", json=second_payload).status_code == 201
    assert db.scalar(select(func.count()).select_from(TestCase)) == 3
    assert db.scalar(select(func.count()).select_from(Run)) == 2
    assert db.scalar(select(func.count()).select_from(Finding)) == 4
    test_case = db.scalar(select(TestCase).where(TestCase.test_case_id == "JB-001"))
    assert test_case is not None
    assert len(test_case.findings) == 2


def test_same_test_case_id_twice_in_one_payload_is_rejected(
    client,
    sample_payload: dict,
) -> None:
    payload = deepcopy(sample_payload)
    payload["findings"] = [
        sample_payload["findings"][0],
        {**sample_payload["findings"][0], "actual_output": "another"},
    ]
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_invalid_risk_score_returns_validation_error(
    client,
    sample_payload: dict,
) -> None:
    payload = deepcopy(sample_payload)
    payload["findings"] = [{**sample_payload["findings"][0], "risk_score": 150}]
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_invalid_severity_returns_validation_error(
    client,
    sample_payload: dict,
) -> None:
    payload = deepcopy(sample_payload)
    payload["findings"] = [{**sample_payload["findings"][0], "severity": "Extreme"}]
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_invalid_status_returns_validation_error(
    client,
    sample_payload: dict,
) -> None:
    payload = deepcopy(sample_payload)
    payload["findings"] = [{**sample_payload["findings"][0], "status": "pending"}]
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_missing_required_field_returns_validation_error(client) -> None:
    payload = make_run_payload()
    del payload["model_version"]
    response = client.post("/runs", json=payload)
    assert response.status_code == 422


def test_conflicting_immutable_test_case_definition_returns_409(
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
    assert (
        response.json()["detail"]
        == "TestCase with test_case_id 'JB-001' already exists "
        "with a different category, sub_category, or prompt"
    )


def test_failed_ingestion_rolls_back_entire_transaction(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
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
    assert db.scalar(select(func.count()).select_from(TestCase)) == 1
    remaining = db.scalar(select(TestCase).where(TestCase.test_case_id == "PI-001"))
    assert remaining is not None
    assert remaining.prompt == "DIFFERENT PROMPT THAT CONFLICTS"
    assert db.scalar(select(TestCase).where(TestCase.test_case_id == "JB-001")) is None


def test_no_partial_run_persisted_after_rollback(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    db.add(
        TestCase(
            test_case_id="DL-001",
            category="Data Leakage",
            sub_category="PII",
            prompt="CONFLICTING PROMPT",
        )
    )
    db.commit()
    assert client.post("/runs", json=sample_payload).status_code == 409
    assert db.scalar(select(Run).where(Run.run_id == "run_001")) is None


def test_existing_reusable_test_cases_not_duplicated_after_failed_ingestion(
    client,
    db: Session,
    sample_payload: dict,
) -> None:
    db.add(
        TestCase(
            test_case_id="JB-001",
            category="Jailbreak",
            sub_category="DAN",
            prompt="Ignore previous instructions...",
        )
    )
    db.add(
        TestCase(
            test_case_id="PI-001",
            category="Prompt Injection",
            sub_category="Direct",
            prompt="CONFLICTING",
        )
    )
    db.commit()
    assert db.scalar(select(func.count()).select_from(TestCase)) == 2

    assert client.post("/runs", json=sample_payload).status_code == 409
    assert db.scalar(select(func.count()).select_from(TestCase)) == 2
    assert db.scalar(select(TestCase).where(TestCase.test_case_id == "DL-001")) is None
