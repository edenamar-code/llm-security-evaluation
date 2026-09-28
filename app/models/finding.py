from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import FindingStatus, Severity

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.test_case import TestCase


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint(
            "run_db_id",
            "test_case_db_id",
            name="uq_findings_run_test_case",
        ),
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100",
            name="ck_findings_risk_score_range",
        ),
        # Composite UNIQUE (run_db_id, test_case_db_id) already indexes run_db_id
        # as a leftmost prefix for "all findings for a run" lookups.
        Index("ix_findings_test_case_db_id", "test_case_db_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_db_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    test_case_db_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actual_output: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity_enum", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(
            FindingStatus,
            name="finding_status_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )

    run: Mapped["Run"] = relationship(back_populates="findings")
    test_case: Mapped["TestCase"] = relationship(back_populates="findings")
