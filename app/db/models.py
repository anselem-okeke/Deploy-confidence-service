import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScoreRun(Base):
    __tablename__ = "score_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    deploy_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    threshold: Mapped[int] = mapped_column(nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    components: Mapped[list["ScoreComponent"]] = relationship(
        back_populates="score_run",
        cascade="all, delete-orphan",
    )


class ScoreComponent(Base):
    __tablename__ = "score_components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    score_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("score_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_name: Mapped[str] = mapped_column(String(100), nullable=False)
    component_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    score_run: Mapped["ScoreRun"] = relationship(back_populates="components")