"""
Endpoints del cierre del ciclo de coaching.

- `/calls/{id}/acknowledgement` — el asesor responde a la evaluación de su
  llamada y, si no está de acuerdo, pide revisión. El jefe contesta con
  `/reply`.
- `/coaching/pending` — las peticiones abiertas, para el jefe.
- `/coaching/my-pending` — lo que el asesor tiene por leer.
- `/coaching/who-to-listen` — qué llamada poner ahora y por qué.
- `/coaching/sessions` — sesiones de coaching sobre una dimensión, cada una
  con su antes y después.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.models.acknowledgement import Acknowledgement
from app.models.agent import Agent
from app.models.call import Call
from app.models.coaching_session import CoachingSession
from app.models.user import User
from app.routers.config import read_qa_thresholds
from app.schemas.coaching import (
    AcknowledgementIn,
    AcknowledgementOut,
    CoachingSessionIn,
    CoachingSessionOut,
    CoachingSessionUpdate,
    CoachingSuggestionOut,
    ListenSuggestionOut,
    ManagerReplyIn,
    PendingCallOut,
)
from app.services import (
    coaching_service,
    coaching_session_service as css,
    dashboard_service as ds,
)

router = APIRouter(tags=["coaching"])


def _get_call(db: Session, call_id: int) -> Call:
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Llamada no encontrada."
        )
    return call


def _ensure_can_view(current_user: User, call: Call) -> None:
    """Un asesor solo accede a sus propias llamadas; un manager a todas."""
    if not current_user.is_manager and call.agent_id != current_user.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para ver esta llamada.",
        )


def build_ack_out(ack: Acknowledgement) -> AcknowledgementOut:
    """Compone la respuesta añadiendo los nombres de las personas implicadas."""
    return AcknowledgementOut(
        id=ack.id,
        call_id=ack.call_id,
        user_id=ack.user_id,
        user_name=ack.user.name if ack.user else None,
        comment=ack.comment,
        review_requested=ack.review_requested,
        manager_reply=ack.manager_reply,
        replied_by_name=ack.replier.name if ack.replier else None,
        replied_at=ack.replied_at,
        created_at=ack.created_at,
        updated_at=ack.updated_at,
        pending_review=ack.pending_review,
    )


# ------------------------ Acuse de recibo del asesor ------------------------


@router.get("/calls/{call_id}/acknowledgement", response_model=AcknowledgementOut | None)
def get_acknowledgement(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el acuse de recibo de la llamada, o `null` si no lo hay."""
    call = _get_call(db, call_id)
    _ensure_can_view(current_user, call)
    if call.acknowledgement is None:
        return None
    return build_ack_out(call.acknowledgement)


@router.put("/calls/{call_id}/acknowledgement", response_model=AcknowledgementOut)
def upsert_acknowledgement(
    call_id: int,
    payload: AcknowledgementIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    El asesor da por leída la evaluación y, si quiere, pide revisión.

    Lo firma **quien la recibió**, no un jefe en su nombre: un acuse de recibo
    ajeno no significaría nada. Por eso solo puede hacerlo el asesor asignado a
    la llamada.
    """
    call = _get_call(db, call_id)

    if call.agent_id is None or call.agent_id != current_user.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el asesor evaluado puede responder a esta evaluación.",
        )
    if call.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta llamada todavía no tiene evaluación a la que responder.",
        )

    ack = call.acknowledgement
    if ack is None:
        ack = Acknowledgement(call_id=call.id)
        db.add(ack)

    ack.user_id = current_user.id
    ack.comment = payload.comment
    # Reabrir la petición borra la respuesta anterior: si el asesor vuelve a
    # pedir revisión, la conversación se reanuda y no queda cerrada de antes.
    if payload.review_requested and not ack.review_requested:
        ack.manager_reply = None
        ack.replied_by = None
        ack.replied_at = None
    ack.review_requested = payload.review_requested

    db.commit()
    db.refresh(ack)
    return build_ack_out(ack)


@router.post(
    "/calls/{call_id}/acknowledgement/reply", response_model=AcknowledgementOut
)
def reply_to_acknowledgement(
    call_id: int,
    payload: ManagerReplyIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """El jefe contesta a la petición de revisión y con eso la cierra."""
    call = _get_call(db, call_id)
    ack = call.acknowledgement
    if ack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El asesor todavía no ha respondido a esta evaluación.",
        )

    ack.manager_reply = payload.reply
    ack.replied_by = current_user.id
    ack.replied_at = datetime.now()

    db.commit()
    db.refresh(ack)
    return build_ack_out(ack)


# ------------------------------- Listados ----------------------------------


@router.get("/coaching/pending", response_model=list[AcknowledgementOut])
def pending_requests(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Peticiones de revisión abiertas: alguien está esperando respuesta."""
    return [
        build_ack_out(a) for a in coaching_service.pending_review_requests(db, limit)
    ]


@router.get("/coaching/my-pending", response_model=list[PendingCallOut])
def my_pending(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Evaluaciones del asesor de las que aún no ha acusado recibo."""
    if current_user.agent_id is None:
        return []
    return [
        PendingCallOut(
            call_id=call.id,
            global_score=analysis.global_score,
            call_date=call.call_date,
            campaign=call.campaign_type,
            created_at=call.created_at,
        )
        for call, analysis in coaching_service.unacknowledged_for_agent(
            db, current_user.agent_id, limit
        )
    ]


@router.get("/coaching/who-to-listen", response_model=list[ListenSuggestionOut])
def who_to_listen(
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Qué llamadas escuchar ahora y por qué. Es con lo que abre el panel."""
    start, end = ds.resolve_window(period, date_from, date_to)
    thresholds = read_qa_thresholds(db)
    return [
        ListenSuggestionOut(**s)
        for s in coaching_service.who_to_listen(db, start, end, thresholds, limit)
    ]


# ------------------------- Sesiones de coaching -------------------------


def _session_out(
    s: CoachingSession, medida: dict, nombres: dict[str, str]
) -> CoachingSessionOut:
    return CoachingSessionOut(
        id=s.id,
        agent_id=s.agent_id,
        agent_name=s.agent.name if s.agent else None,
        dimension_key=s.dimension_key,
        # Si la dimensión ya no está en la rúbrica se enseña la clave: la sesión
        # se hizo y su medida sigue valiendo para las llamadas de entonces.
        dimension_name=nombres.get(s.dimension_key, s.dimension_key),
        held_on=s.held_on,
        notes=s.notes,
        call_id=s.call_id,
        coach_name=s.coach.name if s.coach else None,
        created_at=s.created_at,
        measure=medida,
    )


def _get_session(db: Session, session_id: int) -> CoachingSession:
    sesion = db.get(CoachingSession, session_id)
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión de coaching no encontrada.",
        )
    return sesion


def _validate_fields(
    db: Session,
    agent_id: int,
    dimension_key: str | None,
    held_on: date | None,
    call_id: int | None = None,
) -> None:
    """Comprueba lo que la base de datos no puede comprobar por sí sola."""
    if dimension_key is not None and dimension_key not in css.dimension_names(db):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Esa dimensión no existe en la rúbrica vigente.",
        )
    if held_on is not None and held_on > date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La sesión no puede tener fecha futura: se mide una sesión ya hecha.",
        )
    if call_id is not None:
        call = db.get(Call, call_id)
        if call is None or call.agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La llamada de referencia tiene que ser de este asesor.",
            )


def _one_out(db: Session, sesion: CoachingSession) -> CoachingSessionOut:
    medida = css.measure_many(db, [sesion])[sesion.id]
    return _session_out(sesion, medida, css.dimension_names(db))


@router.get("/coaching/sessions", response_model=list[CoachingSessionOut])
def list_sessions(
    agent_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sesiones de coaching, la más reciente primero, cada una con su medida."""
    if not current_user.is_manager:
        # El asesor solo ve las suyas, pida lo que pida.
        if current_user.agent_id is None:
            return []
        agent_id = current_user.agent_id

    stmt = select(CoachingSession).order_by(
        CoachingSession.held_on.desc(), CoachingSession.id.desc()
    )
    if agent_id is not None:
        stmt = stmt.where(CoachingSession.agent_id == agent_id)
    sesiones = list(db.scalars(stmt.limit(limit)))

    medidas = css.measure_many(db, sesiones)
    nombres = css.dimension_names(db)
    return [_session_out(s, medidas[s.id], nombres) for s in sesiones]


@router.post(
    "/coaching/sessions",
    response_model=CoachingSessionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: CoachingSessionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Registra una sesión de coaching con un asesor sobre una dimensión."""
    if db.get(Agent, payload.agent_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ejecutivo no encontrado."
        )
    _validate_fields(
        db, payload.agent_id, payload.dimension_key, payload.held_on, payload.call_id
    )

    sesion = CoachingSession(
        agent_id=payload.agent_id,
        dimension_key=payload.dimension_key,
        held_on=payload.held_on or date.today(),
        notes=(payload.notes or "").strip() or None,
        call_id=payload.call_id,
        coach_id=current_user.id,
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return _one_out(db, sesion)


@router.get("/coaching/sessions/{session_id}", response_model=CoachingSessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Una sesión con su antes y después. El asesor solo puede ver las suyas."""
    sesion = _get_session(db, session_id)
    if not current_user.is_manager and current_user.agent_id != sesion.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para ver el coaching de otro asesor.",
        )
    return _one_out(db, sesion)


@router.patch("/coaching/sessions/{session_id}", response_model=CoachingSessionOut)
def update_session(
    session_id: int,
    payload: CoachingSessionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Corrige la dimensión, la fecha o las notas de una sesión."""
    sesion = _get_session(db, session_id)
    _validate_fields(db, sesion.agent_id, payload.dimension_key, payload.held_on)
    if payload.dimension_key is not None:
        sesion.dimension_key = payload.dimension_key
    if payload.held_on is not None:
        sesion.held_on = payload.held_on
    if payload.notes is not None:
        sesion.notes = payload.notes.strip() or None
    db.commit()
    db.refresh(sesion)
    return _one_out(db, sesion)


@router.delete(
    "/coaching/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    db.delete(_get_session(db, session_id))
    db.commit()


@router.get(
    "/coaching/suggestions/{agent_id}", response_model=list[CoachingSuggestionOut]
)
def suggestions(
    agent_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Sobre qué dimensiones conviene hacer coaching a este asesor, y por qué."""
    if db.get(Agent, agent_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ejecutivo no encontrado."
        )
    return [CoachingSuggestionOut(**s) for s in css.suggest_dimensions(db, agent_id)]
