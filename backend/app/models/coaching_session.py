"""Modelo de sesión de coaching ligada a un criterio de la rúbrica."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CoachingSession(Base):
    """
    Una sesión de coaching con un asesor sobre **una** dimensión de la rúbrica.

    Ir atada a una dimensión concreta es lo que permite medirla: la misma
    dimensión, puntuada con la misma rúbrica, antes y después de la fecha de la
    sesión. Un coaching «en general» no se puede medir contra nada.

    La medición no se guarda: se calcula al leerla. Así sigue siendo cierta
    cuando entran llamadas nuevas o se corrige una asignación.
    """

    __tablename__ = "coaching_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Clave de la dimensión de la rúbrica (`rubric_config.dimension_key`). Texto
    # y no FK: si la dimensión se borra de la rúbrica, la sesión se conserva.
    dimension_key: Mapped[str] = mapped_column(String(50), nullable=False)
    # Día en que se hizo la sesión. Parte el tiempo en «antes» y «después».
    held_on: Mapped[date] = mapped_column(Date, nullable=False)
    # Qué se trabajó y qué se acordó.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # La llamada que la motivó, si la hubo. Se conserva la sesión si se borra.
    call_id: Mapped[int | None] = mapped_column(
        ForeignKey("calls.id", ondelete="SET NULL"), nullable=True
    )
    coach_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped["Agent"] = relationship()  # noqa: F821
    coach: Mapped["User | None"] = relationship()  # noqa: F821
