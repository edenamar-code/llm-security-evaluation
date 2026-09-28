"""API-level tests for GET /tests/{test_case_id}/stability."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import FindingStatus
from app.schemas.runs import RunCreate
from app.services.ingestion_service import ingest_run
from tests.factories import make_finding_payload, make_run_payload


def _ingest_status_history(
    db: Session,
    *,
    test_case_id: str,
    statuses: list[str],
    run_prefix: str = "stab",
) -> None:
    base = datetime(2026, 9, 20, 10, 0, tzinfo=UTC)
    for index, status in enumerate(statuses):
        payload = make_run_payload(
            run_id=f"{run_prefix}_{index + 1:03d}",
            model_version=f"model-v{index + 1}",
            timestamp=(base + timedelta(hours=index)).isoformat().replace("+00:00", "Z"),
            findings=[
                make_finding_payload(
                    test_case_id=test_case_id,
                    status=status,
                    risk_score=40 if status == "failed" else 90,
                    severity="High" if status == "failed" else "Low",
                )
            ],
        )
        ingest_run(db, RunCreate.model_validate(payload))


def test_unknown_test_case_returns_404(client: TestClient) -> None:
    response = client.get("/tests/MISSING-TC/stability")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_n_less_than_two_is_validation_error(client: TestClient) -> None:
    response = client.get("/tests/JB-001/stability", params={"n": 1})
    assert response.status_code == 422


def test_n_above_maximum_is_validation_error(client: TestClient) -> None:
    response = client.get("/tests/JB-001/stability", params={"n": 101})
    assert response.status_code == 422


def test_one_observation_returns_null_stability(
    client: TestClient,
    db: Session,
) -> None:
    _ingest_status_history(db, test_case_id="ONE-001", statuses=["failed"])

    response = client.get("/tests/ONE-001/stability", params={"n": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["test_case_id"] == "ONE-001"
    assert body["requested_runs"] == 10
    assert body["observations"] == 1
    assert body["stability_score"] is None
    assert body["transitions"] == 0
    assert body["message"] == (
        "At least 2 observations are required to calculate stability."
    )
    assert len(body["history"]) == 1


def test_flaky_alternating_history(client: TestClient, db: Session) -> None:
    _ingest_status_history(
        db,
        test_case_id="FLAKY-001",
        statuses=["failed", "passed", "failed", "passed"],
    )

    response = client.get("/tests/FLAKY-001/stability", params={"n": 4})
    assert response.status_code == 200
    body = response.json()
    assert body["observations"] == 4
    assert body["transitions"] == 3
    assert body["stability_score"] == 0.0
    assert body["message"] is None
    assert [item["status"] for item in body["history"]] == [
        "failed",
        "passed",
        "failed",
        "passed",
    ]
    assert [item["run_id"] for item in body["history"]] == [
        "stab_001",
        "stab_002",
        "stab_003",
        "stab_004",
    ]


def test_stable_all_passed(client: TestClient, db: Session) -> None:
    _ingest_status_history(
        db,
        test_case_id="STABLE-001",
        statuses=["passed", "passed", "passed", "passed"],
    )

    response = client.get("/tests/STABLE-001/stability", params={"n": 4})
    assert response.status_code == 200
    body = response.json()
    assert body["transitions"] == 0
    assert body["stability_score"] == 100.0


def test_latest_n_results_are_used(client: TestClient, db: Session) -> None:
    """History: pass, fail, pass, pass, pass — with n=3 only the last three matter."""
    _ingest_status_history(
        db,
        test_case_id="LATEST-N",
        statuses=["passed", "failed", "passed", "passed", "passed"],
        run_prefix="ln",
    )

    response = client.get("/tests/LATEST-N/stability", params={"n": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["requested_runs"] == 3
    assert body["observations"] == 3
    assert body["transitions"] == 0
    assert body["stability_score"] == 100.0
    assert [item["run_id"] for item in body["history"]] == [
        "ln_003",
        "ln_004",
        "ln_005",
    ]
    assert [item["status"] for item in body["history"]] == [
        "passed",
        "passed",
        "passed",
    ]


def test_n_larger_than_history_uses_available(
    client: TestClient,
    db: Session,
) -> None:
    _ingest_status_history(
        db,
        test_case_id="SHORT-001",
        statuses=["failed", "passed"],
    )

    response = client.get("/tests/SHORT-001/stability", params={"n": 50})
    assert response.status_code == 200
    body = response.json()
    assert body["requested_runs"] == 50
    assert body["observations"] == 2
    assert body["transitions"] == 1
    assert body["stability_score"] == 0.0


def test_history_is_chronological(client: TestClient, db: Session) -> None:
    _ingest_status_history(
        db,
        test_case_id="ORDER-001",
        statuses=["failed", "passed", "failed"],
    )

    response = client.get("/tests/ORDER-001/stability", params={"n": 10})
    assert response.status_code == 200
    body = response.json()
    timestamps = [item["timestamp"] for item in body["history"]]
    assert timestamps == sorted(timestamps)
    assert body["stability_score"] == 0.0
    assert body["transitions"] == 2


def test_default_n_is_ten(client: TestClient, db: Session) -> None:
    statuses = (["passed", "failed"] * 6)[:12]
    _ingest_status_history(db, test_case_id="DEFAULT-N", statuses=statuses)

    response = client.get("/tests/DEFAULT-N/stability")
    assert response.status_code == 200
    body = response.json()
    assert body["requested_runs"] == 10
    assert body["observations"] == 10
    assert len(body["history"]) == 10


def test_equal_timestamps_use_run_id_secondary_order(
    client: TestClient,
    db: Session,
) -> None:
    """Equal timestamps: higher Run.id is treated as newer (DESC secondary sort)."""
    same_ts = "2026-09-27T12:00:00Z"
    for index, status in enumerate(["failed", "passed", "failed"]):
        payload = make_run_payload(
            run_id=f"eq_{index + 1:03d}",
            model_version=f"model-v{index + 1}",
            timestamp=same_ts,
            findings=[
                make_finding_payload(test_case_id="EQ-TS", status=status)
            ],
        )
        ingest_run(db, RunCreate.model_validate(payload))

    response = client.get("/tests/EQ-TS/stability", params={"n": 3})
    assert response.status_code == 200
    body = response.json()
    # Inserted order creates increasing PKs; newest-first by id then reverse
    # chronologically yields insertion order: failed, passed, failed.
    assert [item["run_id"] for item in body["history"]] == [
        "eq_001",
        "eq_002",
        "eq_003",
    ]
    assert body["transitions"] == 2
    assert body["stability_score"] == 0.0
