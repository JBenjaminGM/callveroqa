"""Schemas del cierre del ciclo: acuse de recibo y a quién escuchar hoy."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class AcknowledgementIn(BaseModel):
    """Lo que el asesor envía al responder a una evaluación."""

    comment: str | None = None
    # True si además pide que un jefe revise la nota.
    review_requested: bool = False


class ManagerReplyIn(BaseModel):
    """Respuesta del jefe a una petición de revisión."""

    reply: str = Field(min_length=1)


class AcknowledgementOut(BaseModel):
    """El acuse de recibo de una llamada, con la respuesta del jefe si la hay."""

    id: int
    call_id: int
    user_id: int | None = None
    user_name: str | None = None
    comment: str | None = None
    review_requested: bool
    manager_reply: str | None = None
    replied_by_name: str | None = None
    replied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    # True mientras el asesor pidió revisión y nadie ha contestado.
    pending_review: bool = False

    model_config = {"from_attributes": True}


class ListenSuggestionOut(BaseModel):
    """Una llamada que merece escucharse, con el motivo por el que sale."""

    call_id: int
    agent_id: int | None = None
    agent_name: str | None = None
    campaign: str | None = None
    score: int | None = None
    call_date: date | None = None
    # review_requested | red_unreviewed | below_own_average | never_reviewed_agent
    reason: str
    priority: str
    title: str
    description: str


class PendingCallOut(BaseModel):
    """Una llamada evaluada de la que el asesor todavía no ha acusado recibo."""

    call_id: int
    global_score: int
    call_date: date | None = None
    campaign: str | None = None
    created_at: datetime


# ------------------------- Sesiones de coaching -------------------------


class CoachingSessionIn(BaseModel):
    """Alta de una sesión de coaching."""

    agent_id: int
    dimension_key: str = Field(min_length=1, max_length=50)
    # Por defecto, hoy. No puede ser futura: lo que se mide es una sesión hecha.
    held_on: date | None = None
    notes: str | None = None
    call_id: int | None = None


class CoachingSessionUpdate(BaseModel):
    """Corrección de una sesión ya registrada. Solo cambia lo que se envía."""

    dimension_key: str | None = Field(default=None, min_length=1, max_length=50)
    held_on: date | None = None
    notes: str | None = None


class CoachingPointOut(BaseModel):
    """Una llamada del asesor dentro de la ventana, con su nota en la dimensión."""

    call_id: int
    date: date
    score: int
    phase: str  # before | after


class CoachingMeasureOut(BaseModel):
    """El antes y el después de la sesión sobre su dimensión."""

    window_days: int
    window_start: date
    window_end: date
    window_closed: bool
    before_count: int
    before_avg: float | None = None
    after_count: int
    after_avg: float | None = None
    delta: float | None = None
    team_before_avg: float | None = None
    team_after_avg: float | None = None
    team_delta: float | None = None
    # Mejora del asesor menos la del equipo; sin equipo comparable, la bruta.
    net_delta: float | None = None
    # improved | worsened | no_change | pending | no_baseline
    verdict: str
    points: list[CoachingPointOut] = []


class CoachingSessionOut(BaseModel):
    """Una sesión de coaching con su medición."""

    id: int
    agent_id: int
    agent_name: str | None = None
    dimension_key: str
    dimension_name: str
    held_on: date
    notes: str | None = None
    call_id: int | None = None
    coach_name: str | None = None
    created_at: datetime
    measure: CoachingMeasureOut


class CoachingSuggestionOut(BaseModel):
    """Una dimensión candidata a coaching, con la distancia al equipo."""

    dimension_key: str
    dimension_name: str
    agent_avg: float
    team_avg: float | None = None
    gap: float | None = None
    calls: int
