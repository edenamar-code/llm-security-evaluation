"""API-level tests for GET /diff, including the main 7-bucket regression scenario."""

from sqlalchemy.orm import Session

from app.schemas.diff import DiffReportOut
from app.services.diff_service import compare_runs
from tests.factories import make_finding_payload, make_run_payload

# Exactly one test_case_id per bucket for the main regression scenario.
BASE_RUN = make_run_payload(
    run_id="diff_base",
    model_version="model-v1",
    timestamp="2026-09-27T10:00:00Z",
    findings=[
        make_finding_payload(
            test_case_id="NEW-001",
            category="Jailbreak",
            sub_category="DAN",
            prompt="Jailbreak prompt",
            actual_output="refused",
            severity="Low",
            risk_score=80,
            status="passed",
        ),
        make_finding_payload(
            test_case_id="SOLVED-001",
            category="Prompt Injection",
            sub_category="Direct",
            prompt="Injection prompt",
            actual_output="leaked",
            severity="High",
            risk_score=40,
            status="failed",
        ),
        make_finding_payload(
            test_case_id="WORSENED-001",
            category="Data Leakage",
            sub_category="PII",
            prompt="PII prompt",
            actual_output="partial leak",
            severity="High",
            risk_score=40,
            status="failed",
        ),
        make_finding_payload(
            test_case_id="IMPROVED-001",
            category="Toxicity",
            sub_category="Hate",
            prompt="Toxic prompt",
            actual_output="toxic",
            severity="Critical",
            risk_score=90,
            status="failed",
        ),
        make_finding_payload(
            test_case_id="UNCHANGED-001",
            category="Privacy",
            sub_category="Memory",
            prompt="Privacy prompt",
            actual_output="ok",
            severity="Low",
            risk_score=95,
            status="passed",
        ),
        make_finding_payload(
            test_case_id="BASE-ONLY",
            category="Other",
            sub_category="Misc",
            prompt="Only in base",
            actual_output="failed in base",
            severity="Medium",
            risk_score=50,
            status="failed",
        ),
    ],
)

HEAD_RUN = make_run_payload(
    run_id="diff_head",
    model_version="model-v2",
    timestamp="2026-09-28T10:00:00Z",
    findings=[
        make_finding_payload(
            test_case_id="NEW-001",
            category="Jailbreak",
            sub_category="DAN",
            prompt="Jailbreak prompt",
            actual_output="jailbroken",
            severity="Critical",
            risk_score=20,
            status="failed",
        ),
        make_finding_payload(
            test_case_id="SOLVED-001",
            category="Prompt Injection",
            sub_category="Direct",
            prompt="Injection prompt",
            actual_output="refused",
            severity="Low",
            risk_score=90,
            status="passed",
        ),
        make_finding_payload(
            test_case_id="WORSENED-001",
            category="Data Leakage",
            sub_category="PII",
            prompt="PII prompt",
            actual_output="full leak",
            severity="Critical",
            risk_score=90,
            status="failed",
        ),
        make_finding_payload(
            test_case_id="IMPROVED-001",
            category="Toxicity",
            sub_category="Hate",
            prompt="Toxic prompt",
            actual_output="mild",
            severity="High",
            risk_score=20,
            status="failed",
        ),
        make_finding_payload(
            test_case_id="UNCHANGED-001",
            category="Privacy",
            sub_category="Memory",
            prompt="Privacy prompt",
            actual_output="still ok",
            severity="Low",
            risk_score=97,
            status="passed",
        ),
        make_finding_payload(
            test_case_id="HEAD-ONLY-PASSED",
            category="New",
            sub_category="Suite",
            prompt="Only in head",
            actual_output="passed",
            severity="Low",
            risk_score=99,
            status="passed",
        ),
    ],
)

BUCKETS = [
    "new_issues",
    "solved_issues",
    "worsened_issues",
    "improved_issues",
    "unchanged",
    "missing_in_head",
    "newly_added_passed",
]


def _ids(items: list[dict]) -> set[str]:
    return {item["test_case_id"] for item in items}


def _ingest_pair(client) -> None:
    assert client.post("/runs", json=BASE_RUN).status_code == 201
    assert client.post("/runs", json=HEAD_RUN).status_code == 201


def test_valid_base_head_returns_200(client) -> None:
    _ingest_pair(client)
    response = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    )
    assert response.status_code == 200


def test_response_contains_base_and_head_run_ids(client) -> None:
    _ingest_pair(client)
    body = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    ).json()
    assert body["base_run_id"] == "diff_base"
    assert body["head_run_id"] == "diff_head"


def test_summary_counts_match_bucket_lengths(client) -> None:
    _ingest_pair(client)
    body = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    ).json()
    for bucket in BUCKETS:
        assert body["summary"][bucket] == len(body[bucket])


def test_all_expected_buckets_exist(client) -> None:
    _ingest_pair(client)
    body = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    ).json()
    for bucket in BUCKETS:
        assert bucket in body
        assert bucket in body["summary"]


def test_each_test_case_id_appears_in_exactly_one_bucket(client) -> None:
    _ingest_pair(client)
    body = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    ).json()
    seen: list[str] = []
    for bucket in BUCKETS:
        seen.extend(item["test_case_id"] for item in body[bucket])
    assert len(seen) == len(set(seen))


def test_base_run_not_found_returns_404(client) -> None:
    client.post("/runs", json=HEAD_RUN)
    response = client.get(
        "/diff",
        params={"base_run_id": "missing_base", "head_run_id": "diff_head"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Run with run_id 'missing_base' not found"


def test_head_run_not_found_returns_404(client) -> None:
    client.post("/runs", json=BASE_RUN)
    response = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "missing_head"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Run with run_id 'missing_head' not found"


def test_comparing_same_run_to_itself_returns_400(client) -> None:
    client.post("/runs", json=BASE_RUN)
    response = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_base"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "base_run_id and head_run_id must be different"


def test_response_matches_pydantic_schema(client) -> None:
    _ingest_pair(client)
    body = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    ).json()
    DiffReportOut.model_validate(body)


def test_missing_side_serializes_as_null(client) -> None:
    _ingest_pair(client)
    body = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    ).json()
    missing = body["missing_in_head"][0]
    assert missing["test_case_id"] == "BASE-ONLY"
    assert missing["base"] is not None
    assert missing["head"] is None

    newly = body["newly_added_passed"][0]
    assert newly["test_case_id"] == "HEAD-ONLY-PASSED"
    assert newly["base"] is None
    assert newly["head"] is not None


def test_full_differential_scenario_seven_buckets(client) -> None:
    """Main Component B regression: one test_case_id in each bucket."""
    _ingest_pair(client)
    response = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    )
    assert response.status_code == 200
    body = response.json()

    assert _ids(body["new_issues"]) == {"NEW-001"}
    assert _ids(body["solved_issues"]) == {"SOLVED-001"}
    assert _ids(body["worsened_issues"]) == {"WORSENED-001"}
    assert _ids(body["improved_issues"]) == {"IMPROVED-001"}
    assert _ids(body["unchanged"]) == {"UNCHANGED-001"}
    assert _ids(body["missing_in_head"]) == {"BASE-ONLY"}
    assert _ids(body["newly_added_passed"]) == {"HEAD-ONLY-PASSED"}

    assert body["summary"] == {
        "new_issues": 1,
        "solved_issues": 1,
        "worsened_issues": 1,
        "improved_issues": 1,
        "unchanged": 1,
        "missing_in_head": 1,
        "newly_added_passed": 1,
    }

    worsened = body["worsened_issues"][0]
    assert worsened["base"]["severity"] == "High"
    assert worsened["head"]["severity"] == "Critical"
    assert worsened["head"]["risk_score"] == 90


def test_diff_loading_avoids_n_plus_one_queries(client, db: Session, count_queries) -> None:
    """selectinload should keep query count bounded (not one query per finding)."""
    _ingest_pair(client)
    with count_queries() as counter:
        compare_runs(db, "diff_base", "diff_head")
    # Per run: SELECT run + SELECT findings + SELECT test_cases ≈ 3; two runs ≈ 6.
    assert counter.count <= 8
    assert counter.count >= 2
