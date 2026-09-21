"""Endpoints de configuración: rúbrica de evaluación y settings globales."""

import re
import unicodedata

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings as app_config
from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.models.settings import AppSettings, RubricConfig
from app.models.user import User
from app.schemas.config import (
    RubricDimensionOut,
    RubricUpdateRequest,
    SettingsOut,
    SettingsUpdate,
)

router = APIRouter(prefix="/config", tags=["config"])

# Claves de settings gestionadas por BD y sus valores por defecto.
# El proveedor de IA/transcripción NO se guarda aquí: lo fija la variable de
# entorno (AI_PROVIDER/WHISPER_PROVIDER) y se reporta desde ella en /settings.
SETTINGS_DEFAULTS = {
    "default_language": "es",
}

# Umbrales / metas de QA configurables (persistidos en app_settings, leídos de BD).
QA_THRESHOLD_DEFAULTS = {
    "qa_target_score": 90,
    "qa_low_agent_threshold": 80,
    "qa_red_call_threshold": 60,
    "qa_min_calls_ranking": 5,
    "qa_trend_drop_alert": 5,
}


def read_qa_thresholds(db: Session) -> dict[str, int]:
    """Lee los umbrales de QA desde app_settings, con defaults si faltan o son inválidos."""
    rows = {s.key: s.value for s in db.scalars(select(AppSettings)).all()}
    result: dict[str, int] = {}
    for key, default in QA_THRESHOLD_DEFAULTS.items():
        try:
            result[key] = int(rows.get(key, default))
        except (TypeError, ValueError):
            result[key] = default
    return result


def _slugify(name: str) -> str:
    """Genera una clave estable a partir del nombre (sin tildes, minúsculas)."""
    nfkd = unicodedata.normalize("NFKD", name or "")
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    return (slug or "dim")[:46]


@router.get("/rubric", response_model=list[RubricDimensionOut])
def get_rubric(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Devuelve las dimensiones de la rúbrica con sus pesos y subcriterios."""
    return db.scalars(select(RubricConfig).order_by(RubricConfig.display_order)).all()


@router.put("/rubric", response_model=list[RubricDimensionOut])
def update_rubric(
    payload: RubricUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """
    Reemplaza la rúbrica completa: actualiza las dimensiones existentes, crea las
    nuevas y elimina las que ya no se envían. La IA usará los subcriterios ACTIVOS
    de cada dimensión como guía del análisis. Los pesos deben sumar 100%.
    """
    existing = {r.dimension_key: r for r in db.scalars(select(RubricConfig)).all()}
    seen: set[str] = set()

    for i, dim in enumerate(payload.dimensions):
        # Clave estable: la enviada, o una generada desde el nombre (categoría nueva).
        key = (dim.dimension_key or "").strip() or _slugify(dim.dimension_name)
        base, n = key, 2
        while key in seen:
            key = f"{base[:43]}_{n}"
            n += 1
        seen.add(key)

        criteria = [
            {
                "name": c.name.strip(),
                "enabled": bool(c.enabled),
                "critical": bool(c.critical),
            }
            for c in dim.criteria
            if c.name and c.name.strip()
        ]

        row = existing.get(key)
        if row is None:
            row = RubricConfig(dimension_key=key)
            db.add(row)
        row.dimension_name = dim.dimension_name.strip()
        row.description = dim.description
        row.weight = dim.weight
        row.display_order = i + 1
        row.criteria = criteria

    # Elimina las dimensiones que ya no están en la rúbrica enviada.
    for key, row in existing.items():
        if key not in seen:
            db.delete(row)

    db.commit()
    return db.scalars(select(RubricConfig).order_by(RubricConfig.display_order)).all()


@router.get("/settings", response_model=SettingsOut)
def get_settings_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Devuelve los settings globales actuales."""
    rows = {s.key: s.value for s in db.scalars(select(AppSettings)).all()}
    return SettingsOut(
        default_language=rows.get("default_language", SETTINGS_DEFAULTS["default_language"]),
        # El proveedor de IA y de transcripción los determina la variable de
        # entorno (no la BD): se reportan los valores REALES en uso para que la
        # UI nunca muestre un proveedor distinto al que de verdad analiza.
        ai_provider=app_config.ai_provider,
        whisper_provider=app_config.whisper_provider,
        **read_qa_thresholds(db),
    )


@router.put("/settings", response_model=SettingsOut)
def update_settings_endpoint(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Actualiza uno o varios settings globales (incluidos los umbrales de QA)."""
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in changes.items():
        row = db.get(AppSettings, key)
        if row is None:
            db.add(AppSettings(key=key, value=str(value)))
        else:
            row.value = str(value)
    db.commit()
    return get_settings_endpoint(db=db, _=current_user)
