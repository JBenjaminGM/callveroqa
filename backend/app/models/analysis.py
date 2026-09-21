"""Modelo de análisis IA de una llamada (relación 1:1 con Call)."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Tipo JSON portable: JSONB en PostgreSQL, JSON genérico en otras BD (tests con SQLite).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Analysis(Base):
    """Resultado del análisis IA: scores por dimensión y recomendaciones."""

    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint("global_score >= 0 AND global_score <= 100", name="ck_global_score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    global_score: Mapped[int] = mapped_column(Integer, nullable=False)
    # dimension_scores: {greeting: 85, assertiveness: 72, ...}
    dimension_scores: Mapped[dict] = mapped_column(JSONType, nullable=False)
    # recommendations: [{priority, dimension, title, description}]
    recommendations: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    # dimension_evidence: {greeting: {justification, segments: [i, ...]}, ...}
    # Por qué la IA puso cada nota y en qué segmentos se apoya. Nulo en análisis
    # anteriores a la migración 0011.
    dimension_evidence: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # critical_failures: [{dimension, criterion, segment, reason}]. Si hay alguno,
    # global_score es 0 y uncapped_score guarda la nota que habría tenido.
    critical_failures: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    uncapped_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    call: Mapped["Call"] = relationship(back_populates="analysis")  # noqa: F821
