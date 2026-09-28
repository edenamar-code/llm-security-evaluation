from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FindingStatus


class StabilityHistoryItem(BaseModel):
    """One chronological observation in a stability report."""

    run_id: str
    model_version: str
    timestamp: datetime
    status: FindingStatus


class StabilityReport(BaseModel):
    """Stability / flakiness analysis response for one test case."""

    test_case_id: str
    requested_runs: int
    observations: int
    transitions: int
    stability_score: float | None = None
    message: str | None = None
    history: list[StabilityHistoryItem] = Field(default_factory=list)
