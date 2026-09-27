from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import Run
from app.models.enums import FindingStatus, Severity


class FindingIn(BaseModel):
    test_case_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    sub_category: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    actual_output: str
    severity: Severity
    risk_score: int = Field(ge=0, le=100)
    status: FindingStatus


class RunCreate(BaseModel):
    run_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    timestamp: datetime
    findings: list[FindingIn]

    @model_validator(mode="after")
    def reject_duplicate_test_case_ids(self) -> "RunCreate":
        seen: set[str] = set()
        duplicates: set[str] = set()
        for finding in self.findings:
            if finding.test_case_id in seen:
                duplicates.add(finding.test_case_id)
            seen.add(finding.test_case_id)
        if duplicates:
            ids = ", ".join(sorted(duplicates))
            raise ValueError(
                f"Duplicate test_case_id(s) in findings: {ids}"
            )
        return self


class RunSummaryOut(BaseModel):
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    average_risk_score: float


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    model_version: str
    timestamp: datetime
    summary: RunSummaryOut


def run_to_response(run: Run) -> RunOut:
    """Map a Run ORM instance to the API response shape."""
    return RunOut(
        run_id=run.run_id,
        model_version=run.model_version,
        timestamp=run.timestamp,
        summary=RunSummaryOut(
            total_findings=run.total_findings,
            critical_count=run.critical_count,
            high_count=run.high_count,
            medium_count=run.medium_count,
            low_count=run.low_count,
            average_risk_score=run.average_risk_score,
        ),
    )
