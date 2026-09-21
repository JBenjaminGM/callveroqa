"""
Cierre del ciclo de coaching: a quién escuchar hoy y qué responde el asesor.

Un panel de medias dice cómo va el equipo, pero no qué hacer al abrirlo. Este
módulo responde a la única pregunta con la que un jefe empieza el día: **qué
llamada pongo ahora y por qué**.
"""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acknowledgement import Acknowledgement
from app.models.agent import Agent
from app.models.analysis import Analysis
from app.models.call import Call
from app.models.review import Review
from app.services.dashboard_service import done_analyses
from app.services.evidence_service import rubric_score

# Cuánto tiene que bajar una llamada respecto a la media del propio asesor para
# que merezca escucharse. Por debajo de esto es variación normal, no una señal.
CAIDA_RELEVANTE = 15

# Mínimo de llamadas del asesor en el periodo para que su media signifique algo
# y se pueda comparar una llamada contra ella.
MIN_LLAMADAS_PARA_MEDIA = 3

# Los motivos, de más a menos urgente. Este orden es el que manda en la lista.
ORDEN_DE_MOTIVOS = {
    "review_requested": 0,
    "critical_failed": 1,
    "red_unreviewed": 2,
    "below_own_average": 3,
    "never_reviewed_agent": 4,
}


def _quien(call: Call, nombres: dict[int, str]) -> str:
    """Nombre a mostrar: el registrado, o el que detectó la IA."""
    return (
        nombres.get(call.agent_id)
        or call.detected_agent_name
        or "Sin identificar"
    )


def who_to_listen(
    db: Session,
    start: datetime,
    end: datetime,
    thresholds: dict[str, int],
    limit: int = 5,
) -> list[dict]:
    """
    Las llamadas que más merecen escucharse ahora, cada una con su motivo.

    Cinco motivos, en orden de urgencia. Una llamada aparece **una sola vez**,
    con el motivo más fuerte que le aplique: repetir la misma llamada con tres
    razones distintas convertiría la lista en ruido.

    1. El asesor pidió revisión y nadie le ha contestado. Es lo único de la
       lista donde hay una persona esperando una respuesta.
    2. Llamada suspendida por un criterio crítico y sin escuchar: un
       incumplimiento normativo expone al banco, no solo al asesor.
    3. Llamada en banda roja sin escuchar todavía (sin revisión humana).
    4. Llamada muy por debajo de la media del propio asesor: no es que sea
       malo, es que ese día pasó algo.
    5. Asesor del que no se ha escuchado ninguna llamada en el periodo. No es
       una alarma; es cobertura: nadie sabe cómo está trabajando.
    """
    red_threshold = thresholds["qa_red_call_threshold"]
    rows = done_analyses(db, start, end=end)
    if not rows:
        return []

    nombres = {a.id: a.name for a in db.scalars(select(Agent))}
    call_ids = [c.id for c, _ in rows]

    # Qué llamadas ya tienen revisión humana: escuchadas de verdad por alguien.
    revisadas = set(
        db.scalars(select(Review.call_id).where(Review.call_id.in_(call_ids)))
    )
    acuses = {
        a.call_id: a
        for a in db.scalars(
            select(Acknowledgement).where(Acknowledgement.call_id.in_(call_ids))
        )
    }

    # Media de cada asesor en el periodo, para medir la caída relativa. Sobre la
    # nota de rúbrica (sin auto-fail): las suspendidas ya tienen su propio motivo
    # y sus ceros hundirían la media, escondiendo las demás caídas.
    por_asesor: dict[int, list[int]] = defaultdict(list)
    for call, analysis in rows:
        if call.agent_id is not None:
            por_asesor[call.agent_id].append(rubric_score(analysis))
    medias = {
        agent_id: sum(scores) / len(scores)
        for agent_id, scores in por_asesor.items()
        if len(scores) >= MIN_LLAMADAS_PARA_MEDIA
    }

    sugerencias: dict[int, dict] = {}

    def proponer(call: Call, analysis: Analysis, **campos) -> None:
        """Registra una sugerencia solo si esa llamada no tenía ya un motivo mejor."""
        if call.id in sugerencias:
            return
        sugerencias[call.id] = {
            "call_id": call.id,
            "agent_id": call.agent_id,
            "agent_name": _quien(call, nombres),
            "campaign": call.campaign_type,
            "score": analysis.global_score,
            "call_date": call.call_date,
            **campos,
        }

    recientes = sorted(rows, key=lambda ca: ca[0].created_at, reverse=True)

    # --- 1. Peticiones de revisión abiertas ---
    for call, analysis in recientes:
        acuse = acuses.get(call.id)
        if acuse is not None and acuse.pending_review:
            proponer(
                call,
                analysis,
                reason="review_requested",
                priority="high",
                title="El asesor pidió revisión",
                description=(
                    (acuse.comment or "").strip()
                    or "No está de acuerdo con la evaluación y espera respuesta."
                ),
            )

    # --- 2. Suspendidas por criterio crítico, sin escuchar ---
    # Un incumplimiento normativo es lo más urgente después de una persona
    # esperando respuesta: expone al banco, no solo al asesor.
    for call, analysis in recientes:
        fallos = analysis.critical_failures or []
        if fallos and call.id not in revisadas:
            criterios = ", ".join(f.get("criterion", "") for f in fallos if f.get("criterion"))
            proponer(
                call,
                analysis,
                reason="critical_failed",
                priority="high",
                title="Suspendida por criterio crítico",
                description=(
                    f"{_quien(call, nombres)} · {criterios or 'criterio crítico'}. "
                    "Nadie la ha revisado."
                ),
            )

    # --- 3. Banda roja sin escuchar ---
    for call, analysis in recientes:
        if analysis.global_score < red_threshold and call.id not in revisadas:
            proponer(
                call,
                analysis,
                reason="red_unreviewed",
                priority="high",
                title=f"Banda roja sin escuchar (score {analysis.global_score})",
                description=(
                    f"{_quien(call, nombres)} · "
                    f"{call.campaign_type or 'Sin campaña'}. Nadie la ha revisado."
                ),
            )

    # --- 4. Muy por debajo de la media del propio asesor ---
    for call, analysis in recientes:
        media = medias.get(call.agent_id) if call.agent_id is not None else None
        if media is None:
            continue
        caida = media - rubric_score(analysis)
        if caida >= CAIDA_RELEVANTE:
            proponer(
                call,
                analysis,
                reason="below_own_average",
                priority="medium",
                title=f"{round(caida)} puntos por debajo de su media",
                description=(
                    f"{_quien(call, nombres)} promedia {media:.0f} en el periodo "
                    f"y esta llamada se quedó en {rubric_score(analysis)}."
                ),
            )

    # --- 5. Asesores de los que no se ha escuchado nada ---
    escuchados = {
        call.agent_id
        for call, _ in rows
        if call.id in revisadas and call.agent_id is not None
    }
    for agent_id in por_asesor:
        if agent_id in escuchados:
            continue
        # Su llamada más floja del periodo: si solo se va a escuchar una, esa.
        suyas = [(c, a) for c, a in rows if c.agent_id == agent_id]
        call, analysis = min(suyas, key=lambda ca: ca[1].global_score)
        proponer(
            call,
            analysis,
            reason="never_reviewed_agent",
            priority="low",
            title=f"Nadie ha escuchado a {nombres.get(agent_id, 'este asesor')}",
            description=(
                f"{len(suyas)} llamadas evaluadas en el periodo y ninguna "
                "revisada. Esta es la más floja."
            ),
        )

    # Manda el motivo, no la nota. Una llamada roja siempre tendrá peor score
    # que una donde el asesor pidió revisión, y ordenar por nota la colaría por
    # delante: pero en la segunda hay una persona esperando una respuesta.
    # Dentro de un mismo motivo sí decide la nota, la peor primero.
    return sorted(
        sugerencias.values(),
        key=lambda s: (ORDEN_DE_MOTIVOS[s["reason"]], s["score"] or 0),
    )[:limit]


def pending_review_requests(db: Session, limit: int = 20) -> list[Acknowledgement]:
    """Peticiones de revisión que el asesor abrió y nadie ha contestado."""
    stmt = (
        select(Acknowledgement)
        .where(Acknowledgement.review_requested.is_(True))
        .where(Acknowledgement.replied_at.is_(None))
        .order_by(Acknowledgement.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def unacknowledged_for_agent(
    db: Session, agent_id: int, limit: int = 20
) -> list[tuple[Call, Analysis]]:
    """
    Llamadas del asesor ya evaluadas de las que todavía no ha acusado recibo.

    Es lo que su panel le pone delante: lo que tiene pendiente de leer, no una
    media más.
    """
    stmt = (
        select(Call, Analysis)
        .join(Analysis, Analysis.call_id == Call.id)
        .outerjoin(Acknowledgement, Acknowledgement.call_id == Call.id)
        .where(Call.agent_id == agent_id)
        .where(Acknowledgement.id.is_(None))
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).all())
