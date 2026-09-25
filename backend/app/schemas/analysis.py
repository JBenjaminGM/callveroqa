"""Schemas del análisis IA y la transcripción."""

from pydantic import BaseModel, field_validator


class Recommendation(BaseModel):
    """Una recomendación accionable generada por la IA."""

    priority: str          # high | medium | low
    dimension: str
    title: str
    description: str


class TranscriptionSegment(BaseModel):
    """Un segmento de la transcripción con timestamps y hablante."""

    start: float
    end: float
    speaker: str           # agent | customer
    text: str


class TranscriptionOut(BaseModel):
    """Transcripción completa de una llamada."""

    full_text: str
    segments: list[TranscriptionSegment] = []
    language: str | None = None

    model_config = {"from_attributes": True}


class DimensionEvidence(BaseModel):
    """Por qué la IA puso una nota y en qué segmentos (índices) se apoya."""

    justification: str = ""
    segments: list[int] = []


class CriticalFailure(BaseModel):
    """Un criterio crítico (auto-fail) incumplido."""

    dimension: str
    criterion: str
    segment: int | None = None
    reason: str = ""


class AnalysisOut(BaseModel):
    """Resultado del análisis IA de una llamada."""

    global_score: int
    dimension_scores: dict[str, int]
    dimension_evidence: dict[str, DimensionEvidence] | None = None
    critical_failures: list[CriticalFailure] | None = None
    # Nota que habría tenido sin el auto-fail (solo si hay critical_failures).
    uncapped_score: int | None = None
    # Dimensiones que no aplicaban a esta llamada: sin nota y fuera del global.
    not_applicable: list[str] | None = None
    recommendations: list[Recommendation] = []
    summary: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    team_average: dict[str, float] | None = None

    model_config = {"from_attributes": True}

    @field_validator("recommendations", mode="before")
    @classmethod
    def _sin_recomendaciones(cls, v):
        # La columna admite nulo; sin esto, un análisis sin recomendaciones
        # tumbaba el detalle de la llamada con un 500.
        return v or []
