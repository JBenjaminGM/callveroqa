"""Lógica de negocio de llamadas: creación, listado y consultas."""

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import Analysis
from app.models.call import Call, CallStatus

logger = logging.getLogger("callveroqa.calls")

# Progreso aproximado (%) asociado a cada estado, para el polling del frontend.
STATUS_PROGRESS = {
    CallStatus.QUEUED: 5,
    CallStatus.TRANSCRIBING: 40,
    CallStatus.ANALYZING: 75,
    CallStatus.DONE: 100,
    CallStatus.ERROR: 100,
}


# Tiempo máximo que puede tardar una llamada en procesarse. Pasado ese margen se
# da por perdida: si el proveedor de IA no responde o el proceso muere a medias,
# la llamada se quedaría en "Transcribiendo" para siempre sin avisar a nadie.
MINUTOS_MAXIMOS_DE_PROCESO = 20

ESTADOS_EN_PROCESO = (CallStatus.QUEUED, CallStatus.TRANSCRIBING, CallStatus.ANALYZING)


def rescatar_atascadas(db: Session) -> int:
    """
    Marca como error las llamadas que llevan demasiado tiempo procesándose.

    Devuelve cuántas ha rescatado. Es una sola UPDATE sobre una columna indexada,
    así que sale gratis llamarla al abrir el listado.
    """
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)  # las columnas son naive
    limite = ahora - timedelta(minutes=MINUTOS_MAXIMOS_DE_PROCESO)
    resultado = db.execute(
        update(Call)
        .where(Call.status.in_(ESTADOS_EN_PROCESO), Call.created_at < limite)
        .values(
            status=CallStatus.ERROR,
            error_message=(
                f"El procesamiento superó los {MINUTOS_MAXIMOS_DE_PROCESO} minutos "
                "y se dio por perdido. Vuelve a intentarlo."
            ),
        )
    )
    if resultado.rowcount:
        db.commit()
        logger.warning("Rescatadas %s llamadas atascadas.", resultado.rowcount)
    return resultado.rowcount or 0


def get_call(db: Session, call_id: int) -> Call | None:
    """Devuelve una llamada con su transcripción y análisis precargados."""
    query = (
        select(Call)
        .where(Call.id == call_id)
        .options(
            selectinload(Call.agent),
            selectinload(Call.campaign),
            selectinload(Call.transcription),
            selectinload(Call.analysis),
        )
    )
    return db.scalar(query)


def list_calls(
    db: Session,
    *,
    agent_id: int | None = None,
    status: CallStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_score: int | None = None,
    max_score: int | None = None,
    unassigned: bool | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[Call], int]:
    """
    Lista llamadas con filtros y paginación.

    El filtro de fechas se aplica sobre la fecha de subida (created_at).
    Devuelve (lista de llamadas de la página, total de resultados).
    """
    query = select(Call).options(
        selectinload(Call.agent), selectinload(Call.analysis)
    )

    if agent_id is not None:
        query = query.where(Call.agent_id == agent_id)
    if unassigned:
        query = query.where(Call.agent_id.is_(None))
    if status is not None:
        query = query.where(Call.status == status)
    if date_from is not None:
        query = query.where(Call.created_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        # Se incluye todo el día 'date_to' sumando un día al límite superior.
        query = query.where(
            Call.created_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )

    # El filtro por score requiere unir con la tabla de análisis.
    if min_score is not None or max_score is not None:
        query = query.join(Analysis, Analysis.call_id == Call.id)
        if min_score is not None:
            query = query.where(Analysis.global_score >= min_score)
        if max_score is not None:
            query = query.where(Analysis.global_score <= max_score)

    # Conteo total (antes de paginar).
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # Ordenamiento seguro: solo se permiten columnas conocidas.
    sort_column = {
        "created_at": Call.created_at,
        "call_date": Call.call_date,
        "duration_seconds": Call.duration_seconds,
        "status": Call.status,
    }.get(sort_by, Call.created_at)
    query = query.order_by(
        sort_column.asc() if sort_order == "asc" else sort_column.desc()
    )

    # Paginación.
    query = query.offset((page - 1) * page_size).limit(page_size)
    items = list(db.scalars(query).all())
    return items, total

def get_team_average(db: Session) -> dict[str, float]:
    """
    Calcula el promedio del equipo por dimensión.

    Recorre todos los análisis y promedia cada dimensión. Se usa para
    mostrar la comparativa de una llamada contra el equipo.
    """
    analyses = db.scalars(select(Analysis)).all()
    if not analyses:
        return {}

    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for analysis in analyses:
        for key, score in (analysis.dimension_scores or {}).items():
            sums[key] = sums.get(key, 0.0) + score
            counts[key] = counts.get(key, 0) + 1

    return {key: round(sums[key] / counts[key], 1) for key in sums}
