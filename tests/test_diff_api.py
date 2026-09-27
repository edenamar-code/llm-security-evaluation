BASE_RUN = {
    "run_id": "diff_base",
    "model_version": "model-v1",
    "timestamp": "2026-09-27T10:00:00Z",
    "findings": [
        {
            "test_case_id": "NEW-REGRESSION",
            "category": "Jailbreak",
            "sub_category": "DAN",
            "prompt": "Jailbreak prompt",
            "actual_output": "refused",
            "severity": "Low",
            "risk_score": 80,
            "status": "passed",
        },
        {
            "test_case_id": "SOLVED-001",
            "category": "Prompt Injection",
            "sub_category": "Direct",
            "prompt": "Injection prompt",
            "actual_output": "leaked",
            "severity": "High",
            "risk_score": 40,
            "status": "failed",
        },
        {
            "test_case_id": "WORSENED-001",
            "category": "Data Leakage",
            "sub_category": "PII",
            "prompt": "PII prompt",
            "actual_output": "partial leak",
            "severity": "High",
            "risk_score": 40,
            "status": "failed",
        },
        {
            "test_case_id": "IMPROVED-001",
            "category": "Toxicity",
            "sub_category": "Hate",
            "prompt": "Toxic prompt",
            "actual_output": "toxic",
            "severity": "Critical",
            "risk_score": 90,
            "status": "failed",
        },
        {
            "test_case_id": "UNCHANGED-001",
            "category": "Privacy",
            "sub_category": "Memory",
            "prompt": "Privacy prompt",
            "actual_output": "ok",
            "severity": "Low",
            "risk_score": 95,
            "status": "passed",
        },
        {
            "test_case_id": "BASE-ONLY",
            "category": "Other",
            "sub_category": "Misc",
            "prompt": "Only in base",
            "actual_output": "failed in base",
            "severity": "Medium",
            "risk_score": 50,
            "status": "failed",
        },
    ],
}

HEAD_RUN = {
    "run_id": "diff_head",
    "model_version": "model-v2",
    "timestamp": "2026-09-28T10:00:00Z",
    "findings": [
        {
            "test_case_id": "NEW-REGRESSION",
            "category": "Jailbreak",
            "sub_category": "DAN",
            "prompt": "Jailbreak prompt",
            "actual_output": "jailbroken",
            "severity": "Critical",
            "risk_score": 20,
            "status": "failed",
        },
        {
            "test_case_id": "SOLVED-001",
            "category": "Prompt Injection",
            "sub_category": "Direct",
            "prompt": "Injection prompt",
            "actual_output": "refused",
            "severity": "Low",
            "risk_score": 90,
            "status": "passed",
        },
        {
            "test_case_id": "WORSENED-001",
            "category": "Data Leakage",
            "sub_category": "PII",
            "prompt": "PII prompt",
            "actual_output": "full leak",
            "severity": "Critical",
            "risk_score": 90,
            "status": "failed",
        },
        {
            "test_case_id": "IMPROVED-001",
            "category": "Toxicity",
            "sub_category": "Hate",
            "prompt": "Toxic prompt",
            "actual_output": "mild",
            "severity": "High",
            "risk_score": 20,
            "status": "failed",
        },
        {
            "test_case_id": "UNCHANGED-001",
            "category": "Privacy",
            "sub_category": "Memory",
            "prompt": "Privacy prompt",
            "actual_output": "still ok",
            "severity": "Low",
            "risk_score": 97,
            "status": "passed",
        },
        {
            "test_case_id": "HEAD-ONLY-PASSED",
            "category": "New",
            "sub_category": "Suite",
            "prompt": "Only in head",
            "actual_output": "passed",
            "severity": "Low",
            "risk_score": 99,
            "status": "passed",
        },
        {
            "test_case_id": "HEAD-ONLY-FAILED",
            "category": "New",
            "sub_category": "Bug",
            "prompt": "Brand new failure",
            "actual_output": "failed",
            "severity": "High",
            "risk_score": 35,
            "status": "failed",
        },
    ],
}


def _ids(items: list[dict]) -> set[str]:
    return {item["test_case_id"] for item in items}


def test_diff_same_run_returns_400(client) -> None:
    client.post("/runs", json=BASE_RUN)
    response = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_base"},
    )
    assert response.status_code == 400
    assert "must be different" in response.json()["detail"]


def test_diff_missing_base_returns_404(client) -> None:
    client.post("/runs", json=HEAD_RUN)
    response = client.get(
        "/diff",
        params={"base_run_id": "missing_base", "head_run_id": "diff_head"},
    )
    assert response.status_code == 404
    assert "missing_base" in response.json()["detail"]


def test_diff_missing_head_returns_404(client) -> None:
    client.post("/runs", json=BASE_RUN)
    response = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "missing_head"},
    )
    assert response.status_code == 404
    assert "missing_head" in response.json()["detail"]


def test_diff_end_to_end_classifies_all_buckets(client) -> None:
    assert client.post("/runs", json=BASE_RUN).status_code == 201
    assert client.post("/runs", json=HEAD_RUN).status_code == 201

    response = client.get(
        "/diff",
        params={"base_run_id": "diff_base", "head_run_id": "diff_head"},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["base_run_id"] == "diff_base"
    assert body["head_run_id"] == "diff_head"

    assert _ids(body["new_issues"]) == {"NEW-REGRESSION", "HEAD-ONLY-FAILED"}
    assert _ids(body["solved_issues"]) == {"SOLVED-001"}
    assert _ids(body["worsened_issues"]) == {"WORSENED-001"}
    assert _ids(body["improved_issues"]) == {"IMPROVED-001"}
    assert _ids(body["unchanged"]) == {"UNCHANGED-001"}
    assert _ids(body["missing_in_head"]) == {"BASE-ONLY"}
    assert _ids(body["newly_added_passed"]) == {"HEAD-ONLY-PASSED"}

    assert body["summary"] == {
        "new_issues": 2,
        "solved_issues": 1,
        "worsened_issues": 1,
        "improved_issues": 1,
        "unchanged": 1,
        "missing_in_head": 1,
        "newly_added_passed": 1,
    }

    worsened = next(item for item in body["worsened_issues"] if item["test_case_id"] == "WORSENED-001")
    assert worsened["base"]["severity"] == "High"
    assert worsened["head"]["severity"] == "Critical"
    assert worsened["head"]["risk_score"] == 90
