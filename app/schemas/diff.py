from pydantic import BaseModel, Field

from app.models.enums import FindingStatus, Severity


class FindingSide(BaseModel):
    """One side of a diff comparison (base or head)."""

    status: FindingStatus
    severity: Severity
    risk_score: int


class DiffItem(BaseModel):
    """Single test-case comparison entry in a diff report."""

    test_case_id: str
    category: str | None = None
    sub_category: str | None = None
    base: FindingSide | None = None
    head: FindingSide | None = None


class DiffSummary(BaseModel):
    """Counts of findings in each differential bucket."""

    new_issues: int = 0
    solved_issues: int = 0
    worsened_issues: int = 0
    improved_issues: int = 0
    unchanged: int = 0
    missing_in_head: int = 0
    newly_added_passed: int = 0


class DiffReport(BaseModel):
    """Full differential analysis response."""

    base_run_id: str
    head_run_id: str
    summary: DiffSummary
    new_issues: list[DiffItem] = Field(default_factory=list)
    solved_issues: list[DiffItem] = Field(default_factory=list)
    worsened_issues: list[DiffItem] = Field(default_factory=list)
    improved_issues: list[DiffItem] = Field(default_factory=list)
    unchanged: list[DiffItem] = Field(default_factory=list)
    missing_in_head: list[DiffItem] = Field(default_factory=list)
    newly_added_passed: list[DiffItem] = Field(default_factory=list)
