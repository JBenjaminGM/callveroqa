"""
Revisión humana y calibración.

Dos ideas sostienen todo este módulo:

1. **La nota de la IA no se pisa.** Cuando una persona corrige una llamada se
   crea un registro aparte (`Review`). Las dos notas conviven.
2. **Calibrar es medir la diferencia entre ambas**, dimensión a dimensión. Si
   una dimensión concreta discrepa mucho más que las demás, el problema no
   suele ser la IA ni el revisor: es que ese criterio de la rúbrica está mal
   escrito y cada uno lo entiende a su manera.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.review import Review
from app.models.settings import RubricConfig
from app.services.evidence_service import rubric_score

# Diferencia (en puntos) por debajo de la cual se considera que IA y humano
# están de acuerdo. ±5 sobre 100 es la tolerancia habitual en las sesiones de
# calibración de un call center.
TOLERANCIA_ACUERDO = 5


def load_rubric_weights(db: Session) -> dict[str, float]:
    """Devuelve {dimension_key: peso} de la rúbrica vigente."""
    return {
        row.dimension_key: float(row.weight)
        for row in db.scalars(select(RubricConfig).order_by(RubricConfig.display_order))
    }


def compute_global_score(dimension_scores: dict[str, int], weights: dict[str, float]) -> int:
    """
    Pondera los scores por dimensión con los pesos de la rúbrica.

    A diferencia del cálculo del análisis IA, aquí se **renormaliza** sobre los
    pesos de las dimensiones realmente puntuadas. Sin eso, si la rúbrica cambió
    después de que la IA analizara la llamada, el revisor puntúa dimensiones sin
    peso definido y el global saldría absurdamente bajo.

    Sin pesos aplicables se cae a la media aritmética, que es lo que cualquiera
    esperaría por defecto.
    """
    if not dimension_scores:
        return 0

    total_weight = sum(weights.get(key, 0.0) for key in dimension_scores)
    if total_weight <= 0:
        media = sum(dimension_scores.values()) / len(dimension_scores)
        return max(0, min(100, round(media)))

    total = sum(
        score * weights.get(key, 0.0) for key, score in dimension_scores.items()
    )
    return max(0, min(100, round(total / total_weight)))


def _period_start(period: str) -> date | None:
    """Traduce un periodo ('7d', '30d', '90d', 'all') a su fecha de inicio."""
    dias = {"7d": 7, "30d": 30, "90d": 90}.get(period)
    if dias is None:
        return None
    # Las columnas de fecha son naive: nunca comparar con un datetime con zona.
    return (datetime.now() - timedelta(days=dias)).date()


def _pairs(db: Session, period: str, campaign: str | None, only_blind: bool):
    """
    Devuelve las parejas (revisión, análisis) comparables del periodo.

    Solo entran llamadas que tienen **las dos** notas: sin nota de la IA no hay
    nada con lo que comparar.
    """
    stmt = (
        select(Review, Analysis, Call)
        .join(Call, Review.call_id == Call.id)
        .join(Analysis, Analysis.call_id == Call.id)
    )

    desde = _period_start(period)
    if desde is not None:
        stmt = stmt.where(Call.call_date >= desde)
    if campaign:
        stmt = stmt.where(Call.campaign_type == campaign)
    if only_blind:
        stmt = stmt.where(Review.blind.is_(True))

    return db.execute(stmt).all()


def agreement_report(
    db: Session,
    period: str = "30d",
    campaign: str | None = None,
    only_blind: bool = False,
    tolerance: int = TOLERANCIA_ACUERDO,
) -> dict:
    """
    Informe de acuerdo IA-humano, global y por dimensión.

    Por cada dimensión se calculan tres números distintos a propósito:

    - **sesgo** (humano − IA): hacia qué lado se desvía la IA. Negativo = la IA
      puntúa más alto que la persona.
    - **desviación media** (media de |humano − IA|): cuánto se desvía, sin que
      un error hacia arriba cancele uno hacia abajo. Es el que ordena la lista.
    - **acuerdo %**: en qué proporción de llamadas la diferencia cabe dentro de
      la tolerancia.

    El sesgo solo puede cancelarse; la desviación media no. Por eso una
    dimensión puede tener sesgo casi cero y aun así ser la peor calibrada.
    """
    filas = _pairs(db, period, campaign, only_blind)

    por_dimension: dict[str, list[tuple[int, int]]] = {}
    global_pairs: list[tuple[int, int]] = []

    for review, analysis, _call in filas:
        # Contra la nota de rúbrica de la IA (sin auto-fail): ver rubric_score.
        global_pairs.append((int(review.global_score), rubric_score(analysis)))
        humanos = review.dimension_scores or {}
        ia = analysis.dimension_scores or {}
        for key, human_score in humanos.items():
            if key not in ia:
                continue
            por_dimension.setdefault(key, []).append(
                (int(human_score), int(ia[key]))
            )

    nombres = {
        row.dimension_key: row.dimension_name
        for row in db.scalars(select(RubricConfig))
    }

    dimensiones = [
        _stats(key, nombres.get(key, key), pares, tolerance)
        for key, pares in por_dimension.items()
    ]
    # De peor a mejor calibrada: la primera es la que hay que revisar.
    dimensiones.sort(key=lambda d: d["mean_abs_diff"], reverse=True)

    resumen = _stats("global", "Global", global_pairs, tolerance)

    return {
        "reviews_count": len(filas),
        "blind_only": only_blind,
        "tolerance": tolerance,
        "human_avg": resumen["human_avg"],
        "ai_avg": resumen["ai_avg"],
        "bias": resumen["bias"],
        "mean_abs_diff": resumen["mean_abs_diff"],
        "agreement_pct": resumen["agreement_pct"],
        "dimensions": dimensiones,
        # La dimensión peor calibrada, si hay datos suficientes para señalarla.
        "worst_dimension": dimensiones[0]["dimension_key"] if dimensiones else None,
    }


def _stats(
    key: str, name: str, pares: list[tuple[int, int]], tolerance: int
) -> dict:
    """Estadísticos de acuerdo para una lista de parejas (humano, IA)."""
    n = len(pares)
    if n == 0:
        return {
            "dimension_key": key,
            "dimension_name": name,
            "count": 0,
            "human_avg": None,
            "ai_avg": None,
            "bias": None,
            "mean_abs_diff": 0.0,
            "agreement_pct": None,
        }

    human_avg = sum(h for h, _ in pares) / n
    ai_avg = sum(a for _, a in pares) / n
    mad = sum(abs(h - a) for h, a in pares) / n
    dentro = sum(1 for h, a in pares if abs(h - a) <= tolerance)

    return {
        "dimension_key": key,
        "dimension_name": name,
        "count": n,
        "human_avg": round(human_avg, 1),
        "ai_avg": round(ai_avg, 1),
        "bias": round(human_avg - ai_avg, 1),
        "mean_abs_diff": round(mad, 1),
        "agreement_pct": round(100 * dentro / n, 1),
    }


def calibration_queue(db: Session, limit: int = 20) -> list[Call]:
    """
    Llamadas listas para calibrar: analizadas y todavía sin revisión humana.

    Se devuelven de la más reciente a la más antigua. Deliberadamente **no** se
    ordenan por score: elegir las peores primero sesgaría la muestra y el
    informe de acuerdo dejaría de representar al conjunto.
    """
    stmt = (
        select(Call)
        .join(Analysis, Analysis.call_id == Call.id)
        .outerjoin(Review, Review.call_id == Call.id)
        .where(Call.status == CallStatus.DONE)
        .where(Review.id.is_(None))
        .options(selectinload(Call.agent))
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))
