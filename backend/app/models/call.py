"""Modelo de llamada subida para análisis."""

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.settings import JSONType


class CallStatus(str, enum.Enum):
    """Estados posibles del procesamiento de una llamada."""

    QUEUED = "QUEUED"
    TRANSCRIBING = "TRANSCRIBING"
    ANALYZING = "ANALYZING"
    DONE = "DONE"
    ERROR = "ERROR"


class Call(Base):
    """Una grabación de llamada y su estado de procesamiento."""

    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    # agent_id es nullable: una llamada puede no estar asignada a un ejecutivo
    # registrado todavía (solo se conoce el nombre detectado por la IA).
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    audio_url: Mapped[str] = mapped_column(String(500), nullable=False)
    audio_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Cuándo borró la política de retención la grabación. La transcripción y la
    # nota se conservan: lo que caduca es el audio, no la evaluación.
    audio_deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="es")
    status: Mapped[CallStatus] = mapped_column(
        SAEnum(CallStatus, name="call_status"), default=CallStatus.QUEUED, index=True
    )
    # Nombre del ejecutivo tal como la IA lo detectó en la transcripción.
    # Se conserva aunque la llamada se asigne luego a un ejecutivo registrado.
    detected_agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Persona responsable de la subida del lote (texto libre).
    responsible: Mapped[str | None] = mapped_column(String(255), nullable=True)
    call_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    campaign_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # campaign_id enlaza la llamada con la entidad Campaña (y su nota de producto).
    # Se conserva campaign_type (texto) por compatibilidad y para los filtros del dashboard.
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id"), nullable=True, index=True
    )
    call_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Métricas de conversación deterministas (talk-ratio, silencio, WPM, turnos…)
    # calculadas desde los segmentos de la transcripción. Null para llamadas
    # antiguas: se recalculan al vuelo desde la transcripción al consultarlas.
    conversation_metrics: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    agent: Mapped["Agent | None"] = relationship(back_populates="calls")  # noqa: F821
    campaign: Mapped["Campaign | None"] = relationship(back_populates="calls")  # noqa: F821
    transcription: Mapped["Transcription | None"] = relationship(  # noqa: F821
        back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
    analysis: Mapped["Analysis | None"] = relationship(  # noqa: F821
        back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
    # Revisión humana de la nota. Convive con `analysis`, no lo reemplaza.
    review: Mapped["Review | None"] = relationship(  # noqa: F821
        back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
    # Lo que el asesor responde a la evaluación (y lo que le contesta el jefe).
    acknowledgement: Mapped["Acknowledgement | None"] = relationship(  # noqa: F821
        back_populates="call", uselist=False, cascade="all, delete-orphan"
    )
