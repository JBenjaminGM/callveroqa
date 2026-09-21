"""
Evidencia de cada nota y criterios críticos (auto-fail).

Dos ideas que el mercado de QA da por hechas y que aquí faltaban:

1. **Una nota sin evidencia no se puede discutir.** El jefe no puede hacer
   coaching con un «62 en objeciones» a secas, ni el asesor rebatirlo. La IA
   devuelve, por dimensión, una justificación y los segmentos de la
   transcripción en que se apoya; la interfaz los convierte en saltos al audio.

2. **Hay fallos que no se compensan.** En banca, omitir la TEA o garantizar una
   aprobación no es «un poco peor»: suspende la llamada. Un subcriterio marcado
   como crítico en la rúbrica, si se incumple, deja la nota global en 0.

Todo lo que viene del LLM se sanea aquí: claves que no existen en la rúbrica,
segmentos fuera de rango o críticos que nadie definió se descartan. La IA
propone; la rúbrica decide qué cuenta.
"""

MAX_SEGMENTS_PER_DIMENSION = 3
MAX_JUSTIFICATION_CHARS = 400
MAX_REASON_CHARS = 300


def _segment_index(value, n_segments: int) -> int | None:
    """Índice de segmento válido o None (acepta ints y strings numéricas)."""
    try:
        idx = int(value)
    except (TypeError, ValueError):
        return None
    return idx if 0 <= idx < n_segments else None


def _clip(text, limit: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def normalize_evidence(raw, rubric_keys: list[str], n_segments: int) -> dict:
    """
    Evidencia saneada: {clave: {"justification": str, "segments": [int]}}.

    Solo claves de la rúbrica, segmentos existentes (sin duplicados, en orden,
    como mucho tres) y justificación recortada. Una dimensión sin nada útil no
    aparece: mejor ausente que vacía.
    """
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict] = {}
    for key in rubric_keys:
        item = raw.get(key)
        if not isinstance(item, dict):
            continue
        justification = _clip(item.get("justification"), MAX_JUSTIFICATION_CHARS)
        segments: list[int] = []
        raw_segments = item.get("segments")
        if isinstance(raw_segments, list):
            for value in raw_segments:
                idx = _segment_index(value, n_segments)
                if idx is not None and idx not in segments:
                    segments.append(idx)
        segments = sorted(segments)[:MAX_SEGMENTS_PER_DIMENSION]
        if justification or segments:
            result[key] = {"justification": justification, "segments": segments}
    return result


def critical_criteria(rubric: list[dict]) -> dict[str, set[str]]:
    """Criterios críticos ACTIVOS de la rúbrica, por dimensión (nombres en minúscula)."""
    result: dict[str, set[str]] = {}
    for dim in rubric:
        names = {
            str(c.get("name", "")).strip().lower()
            for c in (dim.get("criteria") or [])
            if c.get("enabled") and c.get("critical") and str(c.get("name", "")).strip()
        }
        if names:
            result[dim["dimension_key"]] = names
    return result


def normalize_critical_failures(
    raw, rubric: list[dict], n_segments: int
) -> list[dict]:
    """
    Incumplimientos críticos saneados: [{dimension, criterion, segment, reason}].

    Solo se aceptan los que corresponden a un criterio crítico activo de la
    rúbrica. Si la IA marca como crítico algo que nadie definió así, se ignora:
    suspender una llamada es una decisión de la rúbrica, no del modelo.
    """
    allowed = critical_criteria(rubric)
    if not allowed or not isinstance(raw, list):
        return []
    # Nombre original (con mayúsculas) de cada criterio, para mostrarlo tal cual.
    display = {
        (dim["dimension_key"], str(c.get("name", "")).strip().lower()): str(c["name"]).strip()
        for dim in rubric
        for c in (dim.get("criteria") or [])
        if c.get("name")
    }
    failures: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        dimension = str(item.get("dimension", "")).strip()
        criterion = str(item.get("criterion", "")).strip().lower()
        if criterion not in allowed.get(dimension, set()):
            continue
        if (dimension, criterion) in seen:
            continue
        seen.add((dimension, criterion))
        failures.append(
            {
                "dimension": dimension,
                "criterion": display.get((dimension, criterion), criterion),
                "segment": _segment_index(item.get("segment"), n_segments),
                "reason": _clip(item.get("reason"), MAX_REASON_CHARS),
            }
        )
    return failures


def rubric_score(analysis) -> int:
    """
    La nota de la rúbrica, sin el auto-fail.

    Calibrar mide si la IA y una persona **puntúan igual la rúbrica**. El
    auto-fail es una regla que se aplica encima, no un juicio del evaluador:
    comparar el 0 de una llamada suspendida con el 72 que puso el jefe daría
    una «diferencia» de 72 puntos que no es desacuerdo, sino la regla. Lo mismo
    para la media de un asesor: un 0 por regla no dice cómo puntúa su rúbrica.
    """
    if analysis.uncapped_score is not None:
        return int(analysis.uncapped_score)
    return int(analysis.global_score)


def apply_auto_fail(global_score: int, failures: list[dict]) -> tuple[int, int | None]:
    """
    (nota_final, nota_sin_penalizar). Con algún crítico incumplido la llamada
    se suspende: nota 0, y se conserva la que habría tenido para mostrarla.
    """
    if failures:
        return 0, global_score
    return global_score, None
