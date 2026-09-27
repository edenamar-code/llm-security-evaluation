from pydantic import BaseModel, Field

from app.models.enums import FindingStatus, Severity


class FindingSideOut(BaseModel):
    status: FindingStatus
    severity: Severity
    risk_score: int


class DiffItemOut(BaseModel):
    test_case_id: str
    category: str | None = None
    sub_category: str | None = None
    base: FindingSideOut | None = None
    head: FindingSideOut | None = None


class DiffSummaryOut(BaseModel):
    new_issues: int = 0
    solved_issues: int = 0
    worsened_issues: int = 0
    improved_issues: int = 0
    unchanged: int = 0
    missing_in_head: int = 0
    newly_added_passed: int = 0


class DiffReportOut(BaseModel):
    base_run_id: str
    head_run_id: str
    summary: DiffSummaryOut
    new_issues: list[DiffItemOut] = Field(default_factory=list)
    solved_issues: list[DiffItemOut] = Field(default_factory=list)
    worsened_issues: list[DiffItemOut] = Field(default_factory=list)
    improved_issues: list[DiffItemOut] = Field(default_factory=list)
    unchanged: list[DiffItemOut] = Field(default_factory=list)
    missing_in_head: list[DiffItemOut] = Field(default_factory=list)
    newly_added_passed: list[DiffItemOut] = Field(default_factory=list)
