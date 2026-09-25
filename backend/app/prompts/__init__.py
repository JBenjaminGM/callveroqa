"""
Prompts para los modelos de lenguaje.

`get_analysis_prompt` selecciona el prompt según el idioma configurado.
"""

from app.prompts.analysis_en import build_analysis_prompt as _build_en
from app.prompts.analysis_es import build_analysis_prompt as _build_es


def get_analysis_prompt(
    segments: list[dict],
    rubric: list[dict],
    language: str,
    product_note: str | None = None,
    topic_catalog: list[str] | None = None,
) -> str:
    """Devuelve el prompt de análisis en el idioma indicado (es por defecto).

    `segments` es la lista de segmentos (con 'text' ya enmascarado).
    `product_note` es la nota de producto de la campaña asignada (opcional).
    `topic_catalog` son los motivos de llamada ya usados, para que la IA
    reutilice uno en vez de inventar una variante del mismo.
    """
    if language.lower().startswith("en"):
        return _build_en(segments, rubric, product_note, topic_catalog)
    return _build_es(segments, rubric, product_note, topic_catalog)
