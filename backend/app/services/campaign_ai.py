"""
Orquestación de IA para campañas: lectura de PDF y extracción/asistencia con el LLM.

Reutiliza la misma factory de proveedores de análisis (`get_analysis_provider`)
para que la nota de producto se procese con el mismo LLM configurado (Groq por
defecto) sin claves ni dependencias adicionales.
"""

import asyncio
import logging

from app.prompts.campaign import build_assist_prompt, build_extraction_prompt
from app.schemas.campaign import CAMPAIGN_FIELD_GUIDE, LIST_FIELDS
from app.services.analysis_service import get_analysis_provider

logger = logging.getLogger("callveroqa.campaigns")

# Claves válidas de la nota de producto (las que devuelve la IA).
_FIELD_KEYS = [key for key, _ in CAMPAIGN_FIELD_GUIDE]


def extract_text_from_pdf(content: bytes) -> str:
    """
    Extrae el texto de un PDF en memoria.

    `pypdf` se importa de forma perezosa para no exigir la dependencia salvo que
    realmente se procese un PDF (y para que los tests puedan mockear esta función).
    """
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(parts).strip()


def llm_json(prompt: str) -> dict:
    """Envía un prompt al LLM configurado y devuelve el JSON ya parseado."""
    provider = get_analysis_provider()
    return asyncio.run(provider.analyze(prompt))


def _coerce_draft(raw: dict) -> dict:
    """
    Normaliza la respuesta del LLM a la forma de un CampaignDraft.

    - Solo conserva claves conocidas.
    - Campos de lista: garantiza list[str] (acepta strings sueltos o separados por saltos de línea).
    - Campos de texto: garantiza str | None (aplana listas si llegan por error).
    """
    draft: dict = {}
    for key in _FIELD_KEYS:
        value = raw.get(key)
        if key in LIST_FIELDS:
            draft[key] = _to_str_list(value)
        else:
            draft[key] = _to_text(value)
    return draft


def _to_str_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [v.strip(" -•\t") for v in value.splitlines()]
        return [v for v in items if v]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _to_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        text = "\n".join(str(v).strip() for v in value if str(v).strip())
        return text or None
    text = str(value).strip()
    return text or None


def extract_campaign_from_pdf(content: bytes, language: str = "es") -> tuple[dict, str | None]:
    """
    Lee un PDF y extrae la nota de producto estructurada.

    Devuelve (borrador, aviso). Si el PDF no tiene texto legible o la IA falla,
    devuelve un borrador vacío y un aviso para que el usuario complete a mano.
    """
    try:
        text = extract_text_from_pdf(content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo leer el PDF de la campaña: %s", exc)
        return _coerce_draft({}), (
            "No se pudo leer el PDF. Completa la nota de producto manualmente."
        )

    if not text or len(text) < 20:
        return _coerce_draft({}), (
            "El PDF no contenía texto legible (¿es un escaneo/imagen?). "
            "Completa la nota de producto manualmente."
        )

    try:
        raw = llm_json(build_extraction_prompt(text, language))
    except Exception as exc:  # noqa: BLE001
        logger.warning("La IA no pudo extraer la nota de producto: %s", exc)
        return _coerce_draft({}), (
            "La IA no pudo analizar el documento. Completa la nota de producto manualmente."
        )

    return _coerce_draft(raw), None


def assist_campaign(description: str, current: dict | None, language: str = "es") -> tuple[dict, str | None]:
    """
    Pide a la IA que complete/mejore la nota de producto a partir de una descripción.

    Devuelve (borrador, aviso).
    """
    try:
        raw = llm_json(build_assist_prompt(description, current or {}, language))
    except Exception as exc:  # noqa: BLE001
        logger.warning("La IA no pudo asistir la nota de producto: %s", exc)
        return _coerce_draft(current or {}), (
            "La IA no está disponible ahora mismo. Completa la nota de producto manualmente."
        )

    return _coerce_draft(raw), None
