"""
Procesamiento de una llamada de extremo a extremo.

Se ejecuta en un worker Celery (local/Docker) o inline vía BackgroundTasks
cuando PROCESS_INLINE=true (Render free, sin worker).

Flujo completo:
  QUEUED -> TRANSCRIBING -> ANALYZING -> DONE  (o ERROR en cualquier punto)

Pasos:
1. Descargar el audio del storage.
2. Transcribir con el proveedor configurado (Groq por defecto).
3. Diarización por contenido del LLM (con heurística de pausas como fallback).
4. Guardar la transcripción.
5. Enmascarar datos sensibles.
6. Construir el prompt y analizar con el LLM configurado.
7. Calcular el score global y guardar el análisis.
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models.agent import Agent
from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.campaign import Campaign
from app.models.settings import RubricConfig
from app.models.transcription import Transcription
from app.prompts import get_analysis_prompt
from app.services.analysis_service import calculate_global_score, get_analysis_provider
from app.services.evidence_service import (
    apply_auto_fail,
    normalize_critical_failures,
    normalize_evidence,
)
from app.services.campaign_service import build_product_note_text
from app.services.conversation_metrics_service import compute_conversation_metrics
from app.services.masking_service import mask_sensitive_data
from app.services.name_matching import find_matching_agent
from app.services.storage_service import get_storage_provider
from app.services.transcription_service import (
    add_speaker_diarization,
    get_transcription_provider,
)
from app.tasks.celery_app import celery_app

logger = logging.getLogger("callveroqa.tasks")


@celery_app.task(name="process_call")
def process_call(call_id: int) -> None:
    """Procesa una llamada de extremo a extremo (worker Celery o inline si PROCESS_INLINE=true)."""
    db = SessionLocal()
    try:
        call = db.get(Call, call_id)
        if call is None:
            logger.error("process_call: la llamada id=%s no existe", call_id)
            return

        try:
            _run_pipeline(db, call)
        except Exception as exc:  # noqa: BLE001
            # Cualquier fallo deja la llamada en estado ERROR con el detalle.
            logger.exception("Error procesando la llamada id=%s", call_id)
            # Si el fallo ocurrió durante un flush/commit, la sesión queda en
            # estado "needs rollback": hay que limpiarla antes de poder escribir,
            # o este commit lanzaría PendingRollbackError y la llamada se quedaría
            # sin marcar como ERROR.
            db.rollback()
            call = db.get(Call, call_id)
            if call is not None:
                call.status = CallStatus.ERROR
                call.error_message = str(exc)[:1000]
                db.commit()
    finally:
        db.close()


def _run_pipeline(db, call: Call) -> None:
    """Ejecuta los pasos de transcripción y análisis de una llamada."""
    # Idempotencia para reintentos: elimina cualquier transcripción/análisis
    # previo de esta llamada. Sin esto, reintentar una llamada que ya había
    # transcrito violaría la restricción UNIQUE(call_id) y volvería a ERROR.
    db.query(Transcription).filter(Transcription.call_id == call.id).delete()
    db.query(Analysis).filter(Analysis.call_id == call.id).delete()

    # ---- 1. Transcripción ----
    call.status = CallStatus.TRANSCRIBING
    db.commit()
    logger.info("Llamada id=%s: transcribiendo", call.id)

    storage = get_storage_provider()
    audio_bytes = storage.load(call.audio_url)

    # El proveedor de transcripción necesita una ruta en disco.
    suffix = os.path.splitext(call.audio_filename or "audio.mp3")[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        transcriber = get_transcription_provider()
        result = asyncio.run(transcriber.transcribe(tmp_path, call.language))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    segments = add_speaker_diarization(result.get("segments", []))
    full_text = result.get("text", "")

    # Duración estimada a partir del último segmento.
    if segments:
        call.duration_seconds = int(segments[-1]["end"])

    transcription = Transcription(
        call_id=call.id,
        full_text=full_text,
        segments=segments,
        language=call.language,
    )
    db.add(transcription)
    db.commit()

    # ---- 2. Análisis IA ----
    call.status = CallStatus.ANALYZING
    db.commit()
    logger.info("Llamada id=%s: analizando", call.id)

    # Enmascarar datos sensibles ANTES de enviar al LLM (por segmento).
    masked_segments = (
        [{"text": mask_sensitive_data(s.get("text", ""))} for s in segments]
        if segments
        else [{"text": mask_sensitive_data(full_text)}]
    )

    rubric_rows = db.scalars(
        select(RubricConfig).order_by(RubricConfig.display_order)
    ).all()
    rubric_list = [
        {
            "dimension_key": r.dimension_key,
            "dimension_name": r.dimension_name,
            "description": r.description,
            "criteria": r.criteria or [],
        }
        for r in rubric_rows
    ]
    rubric_weights = {r.dimension_key: float(r.weight) for r in rubric_rows}

    # Nota de producto de la campaña asignada (si la hay): la IA evalúa la oferta
    # del ejecutivo contra esta plantilla de referencia.
    product_note = None
    if call.campaign_id is not None:
        campaign = db.get(Campaign, call.campaign_id)
        if campaign is not None:
            product_note = build_product_note_text(campaign) or None

    prompt = get_analysis_prompt(
        masked_segments, rubric_list, call.language, product_note=product_note
    )
    provider = get_analysis_provider()
    analysis_result = asyncio.run(provider.analyze(prompt))

    # Diarización por contenido (LLM): corrige la heurística de pausas cuando la
    # lista devuelta cuadra en longitud con los segmentos.
    diarization = analysis_result.get("diarization")
    if segments and isinstance(diarization, list) and diarization:
        # Aplica las etiquetas del LLM por posición. Tolera que la longitud no
        # coincida exactamente: los segmentos sin etiqueta conservan la heurística.
        for i, seg in enumerate(segments):
            if i < len(diarization):
                role = str(diarization[i]).strip().lower()
                seg["speaker"] = "agent" if role.startswith("a") else "customer"
        transcription.segments = list(segments)  # reasignar para detectar el cambio

    # Métricas de conversación deterministas (sobre los segmentos ya diarizados).
    call.conversation_metrics = compute_conversation_metrics(
        segments, call.duration_seconds
    )

    dimension_scores = {
        k: int(v) for k, v in analysis_result.get("dimension_scores", {}).items()
    }
    global_score = calculate_global_score(dimension_scores, rubric_weights)

    # Evidencia de cada nota y criterios críticos, saneados contra la rúbrica.
    n_segments = len(masked_segments)
    dimension_evidence = normalize_evidence(
        analysis_result.get("dimension_evidence"),
        [r["dimension_key"] for r in rubric_list],
        n_segments,
    )
    critical_failures = normalize_critical_failures(
        analysis_result.get("critical_failures"), rubric_list, n_segments
    )
    global_score, uncapped_score = apply_auto_fail(global_score, critical_failures)

    # ---- Detección y emparejamiento del ejecutivo ----
    # La IA detecta el nombre del ejecutivo en la transcripción. Si coincide
    # (de forma difusa) con un ejecutivo registrado, se asigna la llamada a él;
    # si no, se conserva solo el nombre detectado para asignarlo más tarde.
    detected_name = (analysis_result.get("detected_agent_name") or "").strip()
    if detected_name:
        call.detected_agent_name = detected_name
        if call.agent_id is None:
            agents = db.scalars(select(Agent).where(Agent.active.is_(True))).all()
            match, score = find_matching_agent(detected_name, agents)
            if match is not None:
                call.agent_id = match.id
                logger.info(
                    "Llamada id=%s: ejecutivo '%s' emparejado con '%s' (sim=%.2f)",
                    call.id,
                    detected_name,
                    match.name,
                    score,
                )
            else:
                logger.info(
                    "Llamada id=%s: ejecutivo detectado '%s' sin registrar (mejor sim=%.2f)",
                    call.id,
                    detected_name,
                    score,
                )

    analysis = Analysis(
        call_id=call.id,
        global_score=global_score,
        dimension_scores=dimension_scores,
        dimension_evidence=dimension_evidence or None,
        critical_failures=critical_failures or None,
        uncapped_score=uncapped_score,
        recommendations=analysis_result.get("recommendations", []),
        summary=analysis_result.get("summary"),
        ai_provider=_provider_name(),
        ai_model=analysis_result.get("ai_model"),
        tokens_used=analysis_result.get("tokens_used"),
    )
    db.add(analysis)

    # ---- 3. Finalización ----
    call.status = CallStatus.DONE
    call.processed_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Llamada id=%s: procesada (score global=%s)", call.id, global_score)


def _provider_name() -> str:
    """Devuelve el nombre del proveedor de IA configurado."""
    from app.config import settings

    return settings.ai_provider
