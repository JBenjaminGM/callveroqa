"""Endpoints de subida, consulta y procesamiento de llamadas."""

import math
import os
from datetime import date

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.routers.calibration import build_review_out
from app.routers.coaching import build_ack_out
from app.models.agent import Agent
from app.models.call import Call, CallStatus
from app.models.user import User
from app.schemas.analysis import AnalysisOut, TranscriptionOut
from app.schemas.call import (
    AgentRef,
    AssignAgentRequest,
    BatchCreatedOut,
    BulkAssignRequest,
    BulkDeleteRequest,
    BulkResultOut,
    CallCreatedOut,
    CallDetailOut,
    CallListItem,
    CallListOut,
    CallStatusOut,
    CampaignRef,
    ConversationMetricsOut,
)
from app.services import call_service, campaign_service
from app.services.conversation_metrics_service import compute_conversation_metrics
from app.services.call_service import STATUS_PROGRESS
from app.services.name_matching import find_matching_agent, normalize_name
from app.services.pdf_service import generate_call_report
from app.services.storage_service import get_storage_provider
from app.tasks.call_tasks import process_call
from app.utils.audio import validate_audio_file

router = APIRouter(prefix="/calls", tags=["calls"])

# Tipo MIME por extensión, para que el navegador sepa reproducir el audio.
AUDIO_MEDIA_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
}


def _agent_ref(call: Call) -> AgentRef | None:
    """Devuelve la referencia al ejecutivo de la llamada, o None si no está asignado."""
    return AgentRef.model_validate(call.agent) if call.agent else None


def _ensure_can_view_call(current_user: User, call: Call) -> None:
    """Un asesor solo puede ver sus propias llamadas; un manager todas."""
    if not current_user.is_manager and call.agent_id != current_user.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para ver esta llamada.",
        )


def _resolve_campaign(
    db: Session, campaign_id: int | None, campaign: str | None
) -> tuple[int | None, str | None]:
    """
    Resuelve la campaña de una subida.

    - Si se indica `campaign_id`, usa la entidad Campaña: enlaza por id y copia su
      nombre en `campaign_type` (para que el dashboard y los filtros sigan funcionando).
    - Si no, se usa el texto libre `campaign` por compatibilidad con el flujo anterior.
    """
    if campaign_id is not None:
        entity = campaign_service.get_campaign(db, campaign_id)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaña no encontrada.",
            )
        return entity.id, entity.name
    return None, campaign


def _queue_processing(call_id: int, background_tasks: BackgroundTasks) -> None:
    """
    Lanza el procesamiento de una llamada.

    - Con Celery (por defecto): encola la tarea en el worker.
    - Con PROCESS_INLINE=true (despliegue gratis sin worker): la procesa en una
      tarea en segundo plano del propio proceso de la API.
    """
    if settings.process_inline:
        background_tasks.add_task(process_call, call_id)
    else:
        process_call.delay(call_id)


def _save_call(
    db: Session,
    *,
    audio: UploadFile,
    uploaded_by: int,
    campaign_id: int | None,
    campaign_type: str | None,
    comment: str | None,
    responsible: str | None,
    background_tasks: BackgroundTasks,
) -> Call:
    """
    Valida y persiste una llamada, sube el audio y encola su procesamiento.

    La llamada se crea SIN ejecutivo asignado: la IA detectará el nombre del
    ejecutivo durante el análisis y lo emparejará automáticamente.
    """
    content = audio.file.read()
    try:
        validate_audio_file(audio.filename or "", len(content))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    storage = get_storage_provider()
    audio_url = storage.save(content, audio.filename or "audio.mp3")

    call = Call(
        agent_id=None,
        uploaded_by=uploaded_by,
        audio_url=audio_url,
        audio_filename=audio.filename,
        file_size_bytes=len(content),
        campaign_id=campaign_id,
        campaign_type=campaign_type,
        call_reason=comment,
        responsible=responsible,
        status=CallStatus.QUEUED,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    _queue_processing(call.id, background_tasks)
    return call


@router.post("", response_model=CallCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def upload_call(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    campaign: str | None = Form(default=None),
    campaign_id: int | None = Form(default=None),
    comment: str | None = Form(default=None),
    responsible: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """Sube un audio individual y lo encola para análisis."""
    resolved_id, campaign_type = _resolve_campaign(db, campaign_id, campaign)
    call = _save_call(
        db,
        audio=audio,
        uploaded_by=current_user.id,
        campaign_id=resolved_id,
        campaign_type=campaign_type,
        comment=comment,
        responsible=responsible or current_user.name,
        background_tasks=background_tasks,
    )
    return CallCreatedOut(id=call.id, status=call.status, agent_id=call.agent_id)


@router.post("/batch", response_model=BatchCreatedOut, status_code=status.HTTP_202_ACCEPTED)
def upload_calls_batch(
    background_tasks: BackgroundTasks,
    audios: list[UploadFile] = File(...),
    campaign: str | None = Form(default=None),
    campaign_id: int | None = Form(default=None),
    comment: str | None = Form(default=None),
    responsible: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    """
    Sube un grupo de audios para análisis (hasta 20).

    No se asigna ejecutivo: la IA detectará el nombre de cada ejecutivo a
    partir de la transcripción. Solo se indican la campaña, un comentario
    opcional y el responsable de la subida.
    """
    if len(audios) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Máximo 20 archivos por lote.",
        )
    if not audios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecciona al menos un archivo de audio.",
        )

    resolved_id, campaign_type = _resolve_campaign(db, campaign_id, campaign)
    created_ids: list[int] = []
    for audio in audios:
        call = _save_call(
            db,
            audio=audio,
            uploaded_by=current_user.id,
            campaign_id=resolved_id,
            campaign_type=campaign_type,
            comment=comment,
            responsible=responsible or current_user.name,
            background_tasks=background_tasks,
        )
        created_ids.append(call.id)

    return BatchCreatedOut(created_ids=created_ids, count=len(created_ids))


@router.get("", response_model=CallListOut)
def list_calls(
    agent_id: int | None = Query(default=None),
    status_filter: CallStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    min_score: int | None = Query(default=None, ge=0, le=100),
    max_score: int | None = Query(default=None, ge=0, le=100),
    unassigned: bool | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    critical: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listado paginado de llamadas con filtros (incluye filtro por fecha de subida).

    `q` busca en lo que se dijo en la llamada (transcripción) y devuelve el
    fragmento que coincide; `critical=true` deja solo las suspendidas por un
    criterio crítico.
    """
    # Antes de listar se rescatan las que llevan demasiado tiempo procesándose:
    # es la pantalla donde se notaría, y así ninguna queda colgada para siempre.
    call_service.rescatar_atascadas(db)

    # El asesor solo ve sus propias llamadas (se ignora cualquier agent_id pedido).
    if not current_user.is_manager:
        agent_id = current_user.agent_id
        unassigned = False
    items, total = call_service.list_calls(
        db,
        agent_id=agent_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        min_score=min_score,
        max_score=max_score,
        unassigned=unassigned,
        q=q,
        critical=critical,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    list_items = [
        CallListItem(
            id=c.id,
            agent=_agent_ref(c),
            detected_agent_name=c.detected_agent_name,
            call_date=c.call_date,
            duration_seconds=c.duration_seconds,
            status=c.status,
            global_score=c.analysis.global_score if c.analysis else None,
            critical_failed=bool(c.analysis and c.analysis.uncapped_score is not None),
            match_snippet=(
                call_service.match_snippet(c.transcription.full_text, q)
                if q and c.transcription
                else None
            ),
            created_at=c.created_at,
        )
        for c in items
    ]
    total_pages = math.ceil(total / page_size) if total else 0
    return CallListOut(
        items=list_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/bulk/assign", response_model=BulkResultOut)
def bulk_assign(
    payload: BulkAssignRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """
    Asigna varias llamadas al mismo ejecutivo.

    Existe porque hacerlo de una en una no es viable con volumen real: veinte
    llamadas sin asignar son veinte pantallas.
    """
    agent = db.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")
    if not payload.call_ids:
        return {"affected": 0, "skipped": 0}

    encontradas = db.scalars(
        select(Call).where(Call.id.in_(payload.call_ids))
    ).all()
    for call in encontradas:
        call.agent_id = agent.id
    db.commit()
    return {
        "affected": len(encontradas),
        "skipped": len(set(payload.call_ids)) - len(encontradas),
    }


@router.post("/bulk/delete", response_model=BulkResultOut)
def bulk_delete(
    payload: BulkDeleteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Elimina varias llamadas y sus audios."""
    if not payload.call_ids:
        return {"affected": 0, "skipped": 0}

    encontradas = db.scalars(
        select(Call).where(Call.id.in_(payload.call_ids))
    ).all()
    almacen = get_storage_provider()
    for call in encontradas:
        # Si el audio ya no está, el borrado del registro sigue adelante.
        try:
            almacen.delete(call.audio_url)
        except Exception:  # noqa: BLE001
            pass
        db.delete(call)
    db.commit()
    return {
        "affected": len(encontradas),
        "skipped": len(set(payload.call_ids)) - len(encontradas),
    }


@router.get("/{call_id}", response_model=CallDetailOut)
def get_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalle completo de una llamada: metadata + transcripción + análisis."""
    call = call_service.get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada.")
    _ensure_can_view_call(current_user, call)

    # Métricas de conversación: usa las persistidas o las recalcula al vuelo
    # desde la transcripción (llamadas antiguas sin el campo).
    metrics = call.conversation_metrics
    if metrics is None and call.transcription and call.transcription.segments:
        metrics = compute_conversation_metrics(
            call.transcription.segments, call.duration_seconds
        )

    detail = CallDetailOut(
        id=call.id,
        agent=_agent_ref(call),
        detected_agent_name=call.detected_agent_name,
        responsible=call.responsible,
        audio_url=call.audio_url,
        audio_filename=call.audio_filename,
        duration_seconds=call.duration_seconds,
        status=call.status,
        language=call.language,
        call_date=call.call_date,
        campaign_type=call.campaign_type,
        campaign_id=call.campaign_id,
        campaign=CampaignRef.model_validate(call.campaign) if call.campaign else None,
        call_reason=call.call_reason,
        error_message=call.error_message,
        created_at=call.created_at,
        processed_at=call.processed_at,
        conversation_metrics=(
            ConversationMetricsOut.model_validate(metrics) if metrics else None
        ),
        transcription=(
            TranscriptionOut.model_validate(call.transcription)
            if call.transcription
            else None
        ),
        analysis=None,
    )

    if call.analysis is not None:
        analysis = AnalysisOut.model_validate(call.analysis)
        analysis.team_average = call_service.get_team_average(db)
        detail.analysis = analysis

    if call.review is not None:
        detail.review = build_review_out(call, call.review)

    if call.acknowledgement is not None:
        detail.acknowledgement = build_ack_out(call.acknowledgement)

    return detail


@router.get("/{call_id}/status", response_model=CallStatusOut)
def get_call_status(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve solo el estado de procesamiento (endpoint ligero para polling)."""
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada.")
    _ensure_can_view_call(current_user, call)
    return CallStatusOut(
        id=call.id,
        status=call.status,
        progress_percent=STATUS_PROGRESS.get(call.status, 0),
        error_message=call.error_message,
    )


@router.put("/{call_id}/assign", response_model=CallDetailOut)
def assign_call(
    call_id: int,
    payload: AssignAgentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """
    Asigna (o reasigna) una llamada a un ejecutivo registrado.

    Útil cuando la IA detectó un nombre que no estaba en la base de datos y el
    supervisor crea luego al ejecutivo y quiere vincularle sus llamadas.
    """
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada.")

    agent = db.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")

    call.agent_id = agent.id

    # Opcional: asigna también las demás llamadas sin asignar con el mismo nombre.
    if payload.apply_to_same_name and call.detected_agent_name:
        pending = (
            db.query(Call)
            .filter(Call.agent_id.is_(None), Call.detected_agent_name.is_not(None))
            .all()
        )
        target = normalize_name(call.detected_agent_name)
        for other in pending:
            match, _score = find_matching_agent(
                other.detected_agent_name or "", [agent]
            )
            if match is not None or normalize_name(
                other.detected_agent_name or ""
            ) == target:
                other.agent_id = agent.id

    db.commit()
    return get_call(call_id, db=db, current_user=_)  # reutiliza el armado del detalle


@router.post("/{call_id}/retry", status_code=status.HTTP_202_ACCEPTED)
def retry_call(
    call_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Reintenta el procesamiento de una llamada que quedó en estado ERROR."""
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada.")
    if call.status != CallStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden reintentar llamadas en estado ERROR.",
        )

    call.status = CallStatus.QUEUED
    call.error_message = None
    db.commit()
    _queue_processing(call.id, background_tasks)
    return {"id": call.id, "status": call.status}


@router.get("/{call_id}/report.pdf")
def download_report(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera y descarga el reporte PDF de una llamada."""
    call = call_service.get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada.")
    _ensure_can_view_call(current_user, call)

    pdf_bytes = generate_call_report(call)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="reporte_llamada_{call_id}.pdf"'
        },
    )


@router.get("/{call_id}/audio")
def get_call_audio(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve el audio original de la llamada, para reproducirlo en el navegador.

    El `audio_url` guardado es una ruta interna del almacenamiento (disco o S3),
    no una URL pública, así que el archivo se sirve desde aquí aplicando el mismo
    control de acceso que el resto del detalle de la llamada.
    """
    call = call_service.get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada.")
    _ensure_can_view_call(current_user, call)

    try:
        content = get_storage_provider().load(call.audio_url)
    except Exception:  # noqa: BLE001
        # El almacenamiento local es efímero en algunos despliegues: el archivo
        # puede haber desaparecido aunque la llamada siga en la base de datos.
        raise HTTPException(
            status_code=404,
            detail="El archivo de audio ya no está disponible. Vuelve a subir la llamada.",
        )

    extension = os.path.splitext(call.audio_filename or call.audio_url)[1].lower()
    filename = call.audio_filename or f"llamada_{call_id}{extension or '.mp3'}"
    return Response(
        content=content,
        media_type=AUDIO_MEDIA_TYPES.get(extension, "application/octet-stream"),
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "none",
        },
    )


@router.delete("/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_call(
    call_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Elimina una llamada y su audio asociado."""
    call = db.get(Call, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Llamada no encontrada.")

    # Intenta borrar el audio del storage; si falla, no bloquea el borrado.
    try:
        get_storage_provider().delete(call.audio_url)
    except Exception:  # noqa: BLE001
        pass

    db.delete(call)
    db.commit()
    return None
