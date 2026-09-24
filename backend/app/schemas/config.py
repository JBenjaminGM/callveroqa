"""Schemas de configuración: rúbrica (con subcriterios) y settings globales."""

from pydantic import BaseModel, Field, field_validator, model_validator


class RubricCriterion(BaseModel):
    """Un subcriterio (subcategoría) de una dimensión, que se puede activar."""

    name: str
    enabled: bool = True
    # Crítico (auto-fail): incumplirlo suspende la llamada entera (nota global 0),
    # como un incumplimiento normativo en banca. Solo cuenta si está activo.
    critical: bool = False


class RubricDimensionOut(BaseModel):
    """Una dimensión de la rúbrica con sus subcriterios."""

    dimension_key: str
    dimension_name: str
    description: str | None = None
    weight: float
    display_order: int | None = None
    criteria: list[RubricCriterion] = []

    model_config = {"from_attributes": True}

    @field_validator("criteria", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        """La columna JSON puede venir como None; lo normaliza a lista vacía."""
        return v or []


class RubricDimensionUpdate(BaseModel):
    """Una dimensión enviada al guardar la rúbrica.

    `dimension_key` vacío o ausente indica una categoría NUEVA (se genera la clave
    en el backend a partir del nombre).
    """

    dimension_key: str | None = None
    dimension_name: str = Field(min_length=1)
    description: str | None = None
    weight: float = Field(ge=0, le=100)
    criteria: list[RubricCriterion] = []


class RubricUpdateRequest(BaseModel):
    """Rúbrica completa a guardar (reemplaza la actual). Los pesos deben sumar 100."""

    dimensions: list[RubricDimensionUpdate]

    @model_validator(mode="after")
    def _check(self) -> "RubricUpdateRequest":
        if not self.dimensions:
            raise ValueError("La rúbrica debe tener al menos una dimensión.")
        total = sum(d.weight for d in self.dimensions)
        if abs(total - 100.0) > 0.5:
            raise ValueError(
                f"La suma de los pesos debe ser 100%. Suma actual: {total:.2f}%."
            )
        return self


class SettingsOut(BaseModel):
    """Settings globales de la aplicación, incluidos los umbrales de QA."""

    default_language: str
    ai_provider: str
    whisper_provider: str
    # --- Umbrales / metas de calidad (configurables por el jefe) ---
    qa_target_score: int = 90       # meta de score (verde a partir de aquí)
    qa_low_agent_threshold: int = 80  # asesor "requiere atención" por debajo de esto
    qa_red_call_threshold: int = 60   # llamada en banda roja por debajo de esto
    qa_min_calls_ranking: int = 5     # mínimo de llamadas para entrar en rankings
    qa_trend_drop_alert: int = 5      # caída de score (puntos) que dispara alerta
    # Días que se conservan las grabaciones. 0 = no caducan. La transcripción y
    # la nota se conservan siempre: lo que caduca es la voz.
    retention_audio_days: int = 0


class SettingsUpdate(BaseModel):
    """Campos de settings que se pueden actualizar."""

    default_language: str | None = None
    qa_target_score: int | None = Field(default=None, ge=0, le=100)
    qa_low_agent_threshold: int | None = Field(default=None, ge=0, le=100)
    qa_red_call_threshold: int | None = Field(default=None, ge=0, le=100)
    qa_min_calls_ranking: int | None = Field(default=None, ge=1, le=1000)
    qa_trend_drop_alert: int | None = Field(default=None, ge=0, le=100)
    retention_audio_days: int | None = Field(default=None, ge=0, le=3650)


class RetentionRunOut(BaseModel):
    """Resultado de aplicar la política de retención a mano."""

    retention_audio_days: int
    audios_deleted: int
