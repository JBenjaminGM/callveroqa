"""
Endpoints de calibración: revisión humana de una nota y acuerdo IA-humano.

Tres cosas viven aquí:

1. `/calls/{id}/review` — corregir la nota de una llamada. La de la IA no se
   toca: se guarda una segunda nota junto a ella.
2. `/calibration/queue` y `/calibration/calls/{id}` — la sesión a ciegas. El
   segundo endpoint devuelve la llamada **sin** el análisis de la IA, para que
   el score no llegue siquiera al navegador.
3. `/calibration/agreement` — en qué dimensiones discrepan más IA y personas.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.models.call import Call, CallStatus
from app.models.review import Review
from app.models.user import User
from app.schemas.review import (
    AgreementOut,
    BlindCallOut,
    CalibrationCallOut,
    ReviewIn,
    ReviewOut,
)
from app.services import review_service
from app.services.evidence_service import rubric_score

router = APIRouter(tags=["calibration"])


def _get_call(db: Session, call_id: int) -> Call:
    """Recupera la llamada o lanza 404."""
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


def _agent_name(call: Call) -> str | None:
    """Nombre del ejecutivo: el registrado si lo hay, si no el detectado por la IA."""
    if call.agent:
        return call.agent.name
    return call.detected_agent_name


def build_review_out(call: Call, review: Review) -> ReviewOut:
    """
    Compone la respuesta de una revisión añadiendo la nota de la IA y las
    diferencias, que es lo que hace la comparación legible de un vistazo.
    """
    data = ReviewOut(
        id=review.id,
        call_id=review.call_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=review.reviewer.name if review.reviewer else None,
        global_score=review.global_score,
        dimension_scores=review.dimension_scores or {},
        comment=review.comment,
        blind=review.blind,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )

    analysis = call.analysis
    if analysis is None:
        return data

    ia = {k: int(v) for k, v in (analysis.dimension_scores or {}).items()}
    # Se compara contra la nota de rúbrica de la IA, sin el auto-fail: la
    # diferencia debe medir desacuerdo al puntuar, no la regla del crítico.
    ia_global = rubric_score(analysis)
    data.ai_global_score = ia_global
    data.ai_dimension_scores = ia
    data.global_delta = review.global_score - ia_global
    data.dimension_deltas = {
        key: int(score) - ia[key]
        for key, score in (review.dimension_scores or {}).items()
        if key in ia
    }
    return data


# --------------------------- Revisión de una nota ---------------------------


@router.get("/calls/{call_id}/review", response_model=ReviewOut | None)
def get_review(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve la revisión humana de la llamada, o `null` si aún no tiene."""
    call = _get_call(db, call_id)
    _ensure_can_view(current_user, call)
    if call.review is None:
        return None
    return build_review_out(call, call.review)


@router.put("/calls/{call_id}/review", response_model=ReviewOut)
def upsert_review(
    call_id: int,
    payload: ReviewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Crea o actualiza la revisión humana de una llamada.

    El score global no lo manda el cliente: se calcula aquí ponderando con la
    rúbrica vigente, igual que se hace con la nota de la IA. Así las dos notas
    son comparables porque salen de la misma fórmula.
    """
    call = _get_call(db, call_id)

    if call.analysis is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Esta llamada aún no tiene análisis de la IA: no hay nota que "
                "revisar. Espera a que termine de procesarse."
            ),
        )

    weights = review_service.load_rubric_weights(db)
    global_score = review_service.compute_global_score(payload.dimension_scores, weights)

    review = call.review
    if review is None:
        review = Review(call_id=call.id)
        db.add(review)

    review.reviewer_id = current_user.id
    review.global_score = global_score
    review.dimension_scores = payload.dimension_scores
    review.comment = payload.comment
    review.blind = payload.blind

    db.commit()
    db.refresh(review)
    db.refresh(call)
    return build_review_out(call, review)


@router.delete("/calls/{call_id}/review", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    call_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Retira la revisión humana. La nota de la IA queda intacta."""
    call = _get_call(db, call_id)
    if call.review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Esta llamada no tiene revisión humana.",
        )
    db.delete(call.review)
    db.commit()


# ------------------------- Sesión de calibración -----------------------------


@router.get("/calibration/queue", response_model=list[CalibrationCallOut])
def get_queue(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Llamadas ya analizadas que todavía nadie ha revisado."""
    return [
        CalibrationCallOut(
            id=call.id,
            agent_name=_agent_name(call),
            campaign=call.campaign_type,
            call_date=call.call_date,
            duration_seconds=call.duration_seconds,
            created_at=call.created_at,
        )
        for call in review_service.calibration_queue(db, limit=limit)
    ]


@router.get("/calibration/calls/{call_id}", response_model=BlindCallOut)
def get_blind_call(
    call_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """
    La llamada tal como la ve quien puntúa a ciegas: audio y transcripción, sin
    ningún rastro del análisis de la IA.
    """
    call = _get_call(db, call_id)
    if call.status != CallStatus.DONE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta llamada todavía no está procesada.",
        )
    return BlindCallOut(
        id=call.id,
        agent_name=_agent_name(call),
        campaign=call.campaign_type,
        call_date=call.call_date,
        duration_seconds=call.duration_seconds,
        audio_filename=call.audio_filename,
        transcription=call.transcription,
    )


@router.get("/calibration/agreement", response_model=AgreementOut)
def get_agreement(
    period: str = Query("30d", pattern="^(7d|30d|90d|all)$"),
    campaign: str | None = None,
    blind_only: bool = False,
    tolerance: int = Query(review_service.TOLERANCIA_ACUERDO, ge=0, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Acuerdo entre la IA y las revisiones humanas, global y por dimensión."""
    return review_service.agreement_report(
        db,
        period=period,
        campaign=campaign,
        only_blind=blind_only,
        tolerance=tolerance,
    )
