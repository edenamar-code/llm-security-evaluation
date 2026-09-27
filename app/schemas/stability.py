from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FindingStatus


class StabilityHistoryItemOut(BaseModel):
    run_id: str
    model_version: str
    timestamp: datetime
    status: FindingStatus


class StabilityReportOut(BaseModel):
    test_case_id: str
    requested_runs: int
    observations: int
    transitions: int
    stability_score: float | None = None
    pass_rate: float | None = None
    message: str | None = None
    history: list[StabilityHistoryItemOut] = Field(default_factory=list)
