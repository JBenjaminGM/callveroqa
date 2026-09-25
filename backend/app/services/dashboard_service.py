"""
Lógica de analítica agregada del dashboard (KPIs, alertas, recomendaciones).

Centraliza las consultas y los cálculos que comparten los endpoints de
`routers/dashboard.py`, para mantener el router fino y poder testear la
agregación de forma aislada. Todo es determinista y de coste $0 (sin IA).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.agent import Agent
from app.models.analysis import Analysis
from app.models.call import Call, CallStatus
from app.models.settings import RubricConfig
from app.services import critical_service
from app.services.compliance_service import check_product_note_compliance
from app.services.conversation_metrics_service import compute_conversation_metrics

# Días asociados a cada valor del parámetro `period`.
PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90}

# Tope de llamadas a inspeccionar (con transcripción) al generar alertas de
# compliance, para acotar el coste en despliegues con mucho histórico.
_COMPLIANCE_SCAN_LIMIT = 200
# Mínimo de llamadas de un asesor para que entre en una alerta de "bajo umbral"
# (evita el ruido de un único día malo). El ranking usa qa_min_calls_ranking.
_MIN_CALLS_AGENT_ALERT = 3


# --------------------------------------------------------------------------- #
# Ventana temporal y consultas base
# --------------------------------------------------------------------------- #
def utcnow() -> datetime:
    """
    UTC actual como datetime *naive*.

    Las columnas de fecha del modelo son `DateTime` sin zona horaria, así que un
    datetime *aware* no se puede comparar con ellas. Se toma la hora en UTC de
    forma explícita (en lugar del `datetime.utcnow()` obsoleto) y se descarta el
    tzinfo para conservar la semántica naive-UTC de la base de datos.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def resolve_window(
    period: str = "30d",
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[datetime, datetime]:
    """Resuelve la ventana [inicio, fin]. El rango de fechas prima sobre el periodo."""
    end = datetime.combine(date_to, time.max) if date_to else utcnow()
    if date_from:
        start = datetime.combine(date_from, time.min)
    elif date_to:
        start = end - timedelta(days=PERIOD_DAYS.get(period, 30))
    else:
        start = utcnow() - timedelta(days=PERIOD_DAYS.get(period, 30))
    return start, end


def previous_window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Ventana inmediatamente anterior, de la misma duración (para los deltas)."""
    length = end - start
    return start - length, start


def done_analyses(
    db: Session,
    start: datetime,
    end: datetime | None = None,
    agent_id: int | None = None,
    campaign: str | None = None,
) -> list[tuple[Call, Analysis]]:
    """Filas (Call, Analysis) DONE dentro de la ventana y los filtros."""
    query = (
        select(Call, Analysis)
        .join(Analysis, Analysis.call_id == Call.id)
        # Sin esto, cada acceso posterior a call.campaign o call.transcription
        # (las alertas de compliance recorren hasta 200 llamadas) dispara una
        # consulta suelta: cientos de viajes a la base por cada carga del panel.
        .options(
            selectinload(Call.agent),
            selectinload(Call.campaign),
            selectinload(Call.transcription),
        )
        .where(Call.status == CallStatus.DONE, Call.created_at >= start)
    )
    if end is not None:
        query = query.where(Call.created_at <= end)
    if agent_id is not None:
        query = query.where(Call.agent_id == agent_id)
    if campaign:
        query = query.where(Call.campaign_type == campaign)
    return db.execute(query).all()


# --------------------------------------------------------------------------- #
# Agregaciones pequeñas reutilizables
# --------------------------------------------------------------------------- #
def dimension_averages(rows: list[tuple[Call, Analysis]]) -> dict[str, float]:
    """Promedia cada dimensión a partir de una lista de (Call, Analysis)."""
    sums: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for _, analysis in rows:
        for key, score in (analysis.dimension_scores or {}).items():
            sums[key] += score
            counts[key] += 1
    return {k: round(sums[k] / counts[k], 1) for k in sums}


def _sentiment_key(keys) -> str | None:
    """Devuelve la clave de dimensión de sentimiento, si existe en la rúbrica."""
    for key in keys:
        if "sentim" in str(key).lower():
            return key
    return None


def sentiment_average(rows: list[tuple[Call, Analysis]]) -> float | None:
    """Score medio de la dimensión de sentimiento sobre las filas dadas."""
    scores: list[int] = []
    for _, analysis in rows:
        dims = analysis.dimension_scores or {}
        key = _sentiment_key(dims.keys())
        if key is not None:
            scores.append(dims[key])
    return round(sum(scores) / len(scores), 1) if scores else None


def avg_duration_seconds(rows: list[tuple[Call, Analysis]]) -> float | None:
    """Duración media (segundos) de las llamadas con duración conocida."""
    durations = [c.duration_seconds for c, _ in rows if c.duration_seconds]
    return round(sum(durations) / len(durations), 1) if durations else None


def average_score(rows: list[tuple[Call, Analysis]]) -> float:
    """Score global medio de las filas (0 si no hay)."""
    scores = [a.global_score for _, a in rows]
    return round(sum(scores) / len(scores), 1) if scores else 0.0


def trend_delta(
    rows: list[tuple[Call, Analysis]], start: datetime, end: datetime
) -> float | None:
    """Delta de score: media de la 2ª mitad de la ventana menos la 1ª mitad."""
    mid = start + (end - start) / 2
    first = [a.global_score for c, a in rows if c.created_at < mid]
    second = [a.global_score for c, a in rows if c.created_at >= mid]
    if first and second:
        return (sum(second) / len(second)) - (sum(first) / len(first))
    return None


def format_trend(delta: float | None) -> str:
    """Formatea un delta como cadena con signo (p.ej. '+1.3' / '-2.0')."""
    if delta is None:
        return "+0.0"
    return f"{'+' if delta >= 0 else ''}{delta:.1f}"


def conversation_summary(rows: list[tuple[Call, Analysis]]) -> dict | None:
    """Promedia las métricas de conversación persistidas de las llamadas."""
    metrics = [c.conversation_metrics for c, _ in rows if c.conversation_metrics]
    if not metrics:
        return None

    def _avg(field: str) -> float | None:
        vals = [m[field] for m in metrics if m.get(field) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "calls_measured": len(metrics),
        "avg_agent_talk_pct": _avg("agent_talk_pct"),
        "avg_silence_pct": _avg("silence_pct"),
        "avg_talk_to_listen_ratio": _avg("talk_to_listen_ratio"),
        "avg_agent_words_per_minute": _avg("agent_words_per_minute"),
        "avg_longest_monologue_seconds": _avg("longest_agent_monologue_seconds"),
    }


# --------------------------------------------------------------------------- #
# KPIs por campaña
# --------------------------------------------------------------------------- #
def by_campaign(
    db: Session,
    start: datetime,
    end: datetime,
    red_threshold: int,
) -> list[dict]:
    """KPIs por campaña con delta de score vs el periodo anterior."""
    rows = done_analyses(db, start, end=end)
    prev_start, prev_end = previous_window(start, end)
    prev_rows = done_analyses(db, prev_start, end=prev_end)

    def _group(data) -> dict[str, list[tuple[Call, Analysis]]]:
        grouped: dict[str, list] = defaultdict(list)
        for call, analysis in data:
            grouped[call.campaign_type or "Sin campaña"].append((call, analysis))
        return grouped

    current = _group(rows)
    previous = _group(prev_rows)

    result: list[dict] = []
    for name, group in current.items():
        scores = [a.global_score for _, a in group]
        avg = round(sum(scores) / len(scores), 1)
        red = sum(1 for s in scores if s < red_threshold)
        # Suspendidas por criterio crítico: es la cifra de riesgo normativo de
        # la campaña, y no se lee en la media (una suspendida ya cuenta como 0).
        criticas = sum(1 for _, a in group if a.critical_failures)
        prev_group = previous.get(name, [])
        prev_avg = (
            sum(a.global_score for _, a in prev_group) / len(prev_group)
            if prev_group
            else None
        )
        result.append(
            {
                "campaign": name,
                "total_calls": len(group),
                "avg_score": avg,
                "score_delta": round(avg - prev_avg, 1) if prev_avg is not None else None,
                "red_calls": red,
                "red_pct": round(red / len(group) * 100, 1),
                "critical_calls": criticas,
                "critical_pct": round(criticas / len(group) * 100, 1),
                "sentiment": sentiment_average(group),
                "avg_duration_seconds": avg_duration_seconds(group),
            }
        )
    result.sort(key=lambda r: r["avg_score"], reverse=True)
    return result


# --------------------------------------------------------------------------- #
# Top problemas recurrentes (agregación de recomendaciones)
# --------------------------------------------------------------------------- #
def _normalize_title(title: str) -> str:
    return " ".join(str(title or "").lower().split())


def aggregate_recommendations(
    rows: list[tuple[Call, Analysis]], limit: int = 10
) -> list[dict]:
    """Agrupa las recomendaciones por (dimensión, título) y cuenta su frecuencia."""
    groups: dict[tuple[str, str], dict] = {}
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    for _, analysis in rows:
        for rec in analysis.recommendations or []:
            if not isinstance(rec, dict):
                continue
            dim = rec.get("dimension") or "general"
            title = rec.get("title") or "Recomendación"
            key = (str(dim), _normalize_title(title))
            group = groups.setdefault(
                key,
                {
                    "dimension": str(dim),
                    "title": title,
                    "count": 0,
                    "priority": rec.get("priority") or "medium",
                    "sample_description": rec.get("description") or "",
                },
            )
            group["count"] += 1
            # Conserva la prioridad más alta vista y la descripción más larga.
            if priority_rank.get(rec.get("priority"), 1) < priority_rank.get(
                group["priority"], 1
            ):
                group["priority"] = rec.get("priority")
            desc = rec.get("description") or ""
            if len(desc) > len(group["sample_description"]):
                group["sample_description"] = desc
    ordered = sorted(groups.values(), key=lambda g: g["count"], reverse=True)
    return ordered[:limit]


# --------------------------------------------------------------------------- #
# Alertas accionables para el jefe
# --------------------------------------------------------------------------- #
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
# Alertas que hablan de una persona o del equipo, no de una llamada.
_PATTERN_ALERTS = {"critical_trend", "critical_agent", "low_agent", "trend_drop"}


def build_alerts(
    db: Session,
    start: datetime,
    end: datetime,
    thresholds: dict[str, int],
    limit: int = 25,
) -> list[dict]:
    """
    Genera la lista de alertas accionables del periodo:
    asesor bajo umbral, caída de tendencia, llamadas en banda roja, breach de
    compliance / claim prohibido y anomalía de sentimiento.
    """
    low_threshold = thresholds["qa_low_agent_threshold"]
    red_threshold = thresholds["qa_red_call_threshold"]
    drop_alert = thresholds["qa_trend_drop_alert"]

    rows = done_analyses(db, start, end=end)
    alerts: list[dict] = []

    # --- 1 y 2: por asesor registrado (bajo umbral + caída de tendencia) ---
    by_agent: dict[int, list[tuple[Call, Analysis]]] = defaultdict(list)
    for call, analysis in rows:
        if call.agent_id is not None:
            by_agent[call.agent_id].append((call, analysis))

    agent_names = {
        a.id: a.name
        for a in db.scalars(select(Agent)).all()
    }
    for agent_id, group in by_agent.items():
        name = agent_names.get(agent_id, f"Ejecutivo {agent_id}")
        scores = [a.global_score for _, a in group]
        avg = sum(scores) / len(scores)
        if len(group) >= _MIN_CALLS_AGENT_ALERT and avg < low_threshold:
            alerts.append(
                {
                    "type": "low_agent",
                    "severity": "high" if avg < red_threshold else "medium",
                    "title": f"{name} por debajo del umbral",
                    "description": (
                        f"Score medio {avg:.1f} en {len(group)} llamadas "
                        f"(umbral {low_threshold})."
                    ),
                    "agent_id": agent_id,
                    "agent_name": name,
                    "value": round(avg, 1),
                }
            )
        delta = trend_delta(group, start, end)
        if delta is not None and delta <= -drop_alert:
            alerts.append(
                {
                    "type": "trend_drop",
                    "severity": "medium",
                    "title": f"Tendencia a la baja: {name}",
                    "description": (
                        f"El score de {name} cayó {abs(delta):.1f} puntos respecto "
                        "a la primera mitad del periodo."
                    ),
                    "agent_id": agent_id,
                    "agent_name": name,
                    "value": round(delta, 1),
                }
            )

    # --- 3a: suspendidas por criterio crítico ---
    # Van antes y aparte de la banda roja: su nota es 0 por regla, no por
    # calidad, y lo que hay que mirar es el incumplimiento, no el número.
    criticas = sorted(
        [(c, a) for c, a in rows if a.critical_failures],
        key=lambda ca: ca[0].created_at,
        reverse=True,
    )
    for call, analysis in criticas[:8]:
        who = (
            agent_names.get(call.agent_id)
            or call.detected_agent_name
            or "Sin identificar"
        )
        criterios = ", ".join(
            f.get("criterion", "") for f in analysis.critical_failures if f.get("criterion")
        )
        alerts.append(
            {
                "type": "critical_failure",
                "severity": "high",
                "title": "Llamada suspendida por criterio crítico",
                "description": (
                    f"{who} · {criterios or 'criterio crítico'} "
                    f"({call.campaign_type or 'Sin campaña'})."
                ),
                "agent_id": call.agent_id,
                "agent_name": who,
                "call_id": call.id,
                "campaign": call.campaign_type,
                # El valor ordena dentro de la severidad: la nota que habría
                # tenido, para que primero salga la que más se jugaba.
                "value": analysis.uncapped_score or 0,
            }
        )

    # --- 3a bis: el patrón, no la llamada suelta: quién suspende de forma
    # repetida y si la tasa de suspendidas sube (equipo o persona). ---
    alerts.extend(
        critical_service.critical_alerts(
            critical_service.critical_report(rows, start, end, agent_names)
        )
    )

    # --- 3b: llamadas en banda roja (las más recientes, individuales) ---
    red_calls = sorted(
        [
            (c, a)
            for c, a in rows
            if a.global_score < red_threshold and not a.critical_failures
        ],
        key=lambda ca: ca[0].created_at,
        reverse=True,
    )
    for call, analysis in red_calls[:8]:
        who = (
            agent_names.get(call.agent_id)
            or call.detected_agent_name
            or "Sin identificar"
        )
        alerts.append(
            {
                "type": "red_call",
                "severity": "high",
                "title": f"Llamada en banda roja (score {analysis.global_score})",
                "description": f"{who} · {call.campaign_type or 'Sin campaña'}.",
                "agent_id": call.agent_id,
                "agent_name": who,
                "call_id": call.id,
                "campaign": call.campaign_type,
                "value": analysis.global_score,
            }
        )

    # --- 4: compliance de la nota de producto (claims prohibidos / faltantes) ---
    alerts.extend(_compliance_alerts(db, rows, agent_names))

    # --- 5: anomalía de sentimiento (llamadas muy negativas) ---
    for call, analysis in rows:
        dims = analysis.dimension_scores or {}
        key = _sentiment_key(dims.keys())
        if key is not None and dims[key] < red_threshold:
            who = (
                agent_names.get(call.agent_id)
                or call.detected_agent_name
                or "Sin identificar"
            )
            alerts.append(
                {
                    "type": "sentiment_anomaly",
                    "severity": "medium",
                    "title": f"Sentimiento negativo del cliente (score {dims[key]})",
                    "description": f"{who} · {call.campaign_type or 'Sin campaña'}.",
                    "agent_id": call.agent_id,
                    "agent_name": who,
                    "call_id": call.id,
                    "campaign": call.campaign_type,
                    "value": dims[key],
                }
            )

    # Dentro de una severidad, primero los patrones (una persona o el equipo) y
    # después las llamadas sueltas: un patrón resume muchas llamadas, y ordenar
    # solo por `value` los enterraba, porque mezcla unidades (una nota frente a
    # un porcentaje).
    alerts.sort(
        key=lambda al: (
            _SEVERITY_RANK.get(al["severity"], 1),
            0 if al["type"] in _PATTERN_ALERTS else 1,
            -(al.get("value") or 0),
        )
    )
    return alerts[:limit]


def _compliance_alerts(
    db: Session,
    rows: list[tuple[Call, Analysis]],
    agent_names: dict[int, str],
) -> list[dict]:
    """Alertas de compliance: claims prohibidos detectados y frases obligatorias omitidas."""
    alerts: list[dict] = []
    scanned = 0
    # Solo llamadas con campaña asignada (la nota de producto vive en la campaña).
    candidates = [(c, a) for c, a in rows if c.campaign_id is not None]
    candidates.sort(key=lambda ca: ca[0].created_at, reverse=True)
    for call, _analysis in candidates:
        if scanned >= _COMPLIANCE_SCAN_LIMIT:
            break
        campaign = call.campaign
        transcription = call.transcription
        if campaign is None or transcription is None:
            continue
        if not (campaign.mandatory_phrases or campaign.prohibited_claims):
            continue
        scanned += 1
        report = check_product_note_compliance(
            transcription.segments,
            transcription.full_text,
            campaign.mandatory_phrases,
            campaign.prohibited_claims,
        )
        who = (
            agent_names.get(call.agent_id)
            or call.detected_agent_name
            or "Sin identificar"
        )
        if report["prohibited_hits"]:
            claim = report["prohibited_hits"][0]["claim"]
            alerts.append(
                {
                    "type": "prohibited_claim",
                    "severity": "high",
                    "title": "Posible afirmación prohibida",
                    "description": f"{who} · «{claim}» ({campaign.name}).",
                    "agent_id": call.agent_id,
                    "agent_name": who,
                    "call_id": call.id,
                    "campaign": campaign.name,
                    "value": len(report["prohibited_hits"]),
                }
            )
        elif report["mandatory_total"] and report["mandatory_missing"]:
            missing = report["mandatory_missing"]
            # Solo alerta si se omitió al menos la mitad de lo obligatorio.
            if len(missing) >= max(1, report["mandatory_total"] / 2):
                alerts.append(
                    {
                        "type": "compliance_breach",
                        "severity": "medium",
                        "title": "Frases obligatorias omitidas",
                        "description": (
                            f"{who} · {len(missing)}/{report['mandatory_total']} sin "
                            f"cubrir ({campaign.name})."
                        ),
                        "agent_id": call.agent_id,
                        "agent_name": who,
                        "call_id": call.id,
                        "campaign": campaign.name,
                        "value": len(missing),
                    }
                )
    return alerts


# --------------------------------------------------------------------------- #
# Percentil anónimo del asesor dentro de su campaña
# --------------------------------------------------------------------------- #
def agent_percentile(
    db: Session,
    agent: Agent,
    start: datetime,
    end: datetime,
    min_peers: int,
) -> dict:
    """
    Percentil anónimo del asesor entre los demás asesores de SU campaña.

    Se oculta (available=False) si hay menos de `min_peers` asesores con datos
    en la campaña, para no romper el anonimato.
    """
    campaign = agent.campaign
    # Asesores de la misma campaña (incluye al propio).
    peers = db.scalars(
        select(Agent).where(Agent.campaign == campaign)
    ).all() if campaign else [agent]

    peer_avgs: dict[int, float] = {}
    for peer in peers:
        rows = done_analyses(db, start, end=end, agent_id=peer.id)
        if rows:
            peer_avgs[peer.id] = average_score(rows)

    own = peer_avgs.get(agent.id)
    if own is None or len(peer_avgs) < min_peers:
        return {
            "available": False,
            "campaign": campaign,
            "peers_count": len(peer_avgs),
            "percentile": None,
            "agent_avg": own,
            "campaign_avg": (
                round(sum(peer_avgs.values()) / len(peer_avgs), 1) if peer_avgs else None
            ),
            "rank": None,
        }

    others = list(peer_avgs.values())
    at_or_below = sum(1 for v in others if v <= own)
    percentile = round(at_or_below / len(others) * 100)
    rank = sum(1 for v in others if v > own) + 1
    return {
        "available": True,
        "campaign": campaign,
        "peers_count": len(peer_avgs),
        "percentile": percentile,
        "agent_avg": own,
        "campaign_avg": round(sum(others) / len(others), 1),
        "rank": rank,
    }


# --------------------------------------------------------------------------- #
# Recomendaciones agregadas + compliance del asesor
# --------------------------------------------------------------------------- #
def _longest_agent_segment(transcription) -> str | None:
    """Devuelve el texto del segmento del agente con más palabras (como evidencia)."""
    if transcription is None or not transcription.segments:
        return None
    best, best_words = None, 0
    for seg in transcription.segments:
        if not str(seg.get("speaker", "")).strip().lower().startswith("a"):
            continue
        words = len(str(seg.get("text", "")).split())
        if words > best_words:
            best_words, best = words, str(seg.get("text", "")).strip()
    if best and len(best) > 200:
        best = best[:200].rstrip() + "…"
    return best


def agent_recommendations(
    db: Session, agent: Agent, start: datetime, end: datetime
) -> dict:
    """
    Recomendaciones agregadas del asesor (qué cambiar) con frecuencia y evidencia,
    más el desglose por campaña con cumplimiento de la nota de producto.
    """
    rows = done_analyses(db, start, end=end, agent_id=agent.id)

    # --- Recomendaciones por (dimensión, título) con evidencia ---
    groups: dict[tuple[str, str], dict] = {}
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    for call, analysis in rows:
        dims = analysis.dimension_scores or {}
        for rec in analysis.recommendations or []:
            if not isinstance(rec, dict):
                continue
            dim = str(rec.get("dimension") or "general")
            title = rec.get("title") or "Recomendación"
            key = (dim, _normalize_title(title))
            group = groups.setdefault(
                key,
                {
                    "dimension": dim,
                    "title": title,
                    "count": 0,
                    "priority": rec.get("priority") or "medium",
                    "sample_description": rec.get("description") or "",
                    "evidence": None,
                    "_worst_score": 101,
                },
            )
            group["count"] += 1
            if priority_rank.get(rec.get("priority"), 1) < priority_rank.get(
                group["priority"], 1
            ):
                group["priority"] = rec.get("priority")
            desc = rec.get("description") or ""
            if len(desc) > len(group["sample_description"]):
                group["sample_description"] = desc
            # Evidencia: del peor caso de esa dimensión, un segmento del agente.
            dim_score = dims.get(dim, 100)
            if dim_score < group["_worst_score"]:
                group["_worst_score"] = dim_score
                evidence = _longest_agent_segment(call.transcription)
                if evidence:
                    group["evidence"] = evidence

    items = sorted(groups.values(), key=lambda g: g["count"], reverse=True)
    for item in items:
        item.pop("_worst_score", None)

    # --- Desglose por campaña + compliance de la nota de producto ---
    by_camp: dict[str, list[tuple[Call, Analysis]]] = defaultdict(list)
    for call, analysis in rows:
        by_camp[call.campaign_type or "Sin campaña"].append((call, analysis))

    campaigns: list[dict] = []
    for name, group in by_camp.items():
        scores = [a.global_score for _, a in group]
        # Cumplimiento agregado de la nota de producto en esta campaña.
        mandatory_total = 0
        mandatory_covered = 0
        prohibited = 0
        missing_set: set[str] = set()
        measured = 0
        for call, _ in group:
            campaign = call.campaign
            transcription = call.transcription
            if campaign is None or transcription is None:
                continue
            if not (campaign.mandatory_phrases or campaign.prohibited_claims):
                continue
            report = check_product_note_compliance(
                transcription.segments,
                transcription.full_text,
                campaign.mandatory_phrases,
                campaign.prohibited_claims,
            )
            measured += 1
            mandatory_total += report["mandatory_total"]
            mandatory_covered += report["mandatory_covered_count"]
            prohibited += len(report["prohibited_hits"])
            missing_set.update(report["mandatory_missing"])
        campaigns.append(
            {
                "campaign": name,
                "total_calls": len(group),
                "avg_score": round(sum(scores) / len(scores), 1),
                "compliance": (
                    {
                        "calls_measured": measured,
                        "coverage_pct": (
                            round(mandatory_covered / mandatory_total * 100, 1)
                            if mandatory_total
                            else None
                        ),
                        "prohibited_hits": prohibited,
                        "mandatory_missing": sorted(missing_set),
                    }
                    if measured
                    else None
                ),
            }
        )
    campaigns.sort(key=lambda c: c["total_calls"], reverse=True)

    return {"total_calls": len(rows), "recommendations": items, "by_campaign": campaigns}


# --------------------------------------------------------------------------- #
# Exportación del reporte de equipo
# --------------------------------------------------------------------------- #
def team_report(
    db: Session,
    start: datetime,
    end: datetime,
    campaign: str | None,
    red_threshold: int,
) -> tuple[list[str], list[list]]:
    """
    Reporte del equipo listo para exportar: cabeceras y una fila por ejecutivo.

    Agrupa por ejecutivo registrado. Las llamadas todavía sin asignar se agrupan
    bajo el nombre que detectó la IA, para que no desaparezcan del reporte.
    Se ordena de menor a mayor score, que es el orden en el que un jefe quiere
    leerlo: primero quien necesita atención.
    """
    rows = done_analyses(db, start, end, campaign=campaign)

    dimensions = db.scalars(
        select(RubricConfig).order_by(RubricConfig.display_order)
    ).all()
    dimension_keys = [d.dimension_key for d in dimensions]

    agents = {a.id: a for a in db.scalars(select(Agent))}

    grouped: dict[str, list[tuple[Call, Analysis]]] = defaultdict(list)
    for call, analysis in rows:
        agent = agents.get(call.agent_id) if call.agent_id else None
        if agent is not None:
            key = f"agent:{agent.id}"
        else:
            key = f"detected:{(call.detected_agent_name or 'Sin asignar').strip()}"
        grouped[key].append((call, analysis))

    header = [
        "Ejecutivo",
        "Email",
        "Campañas",
        "Registrado",
        "Llamadas",
        "Score promedio",
        *[d.dimension_name for d in dimensions],
        "Llamadas en rojo",
        "% en rojo",
    ]

    table: list[list] = []
    for key, group in grouped.items():
        if key.startswith("agent:"):
            agent = agents[int(key.split(":", 1)[1])]
            name, email, registered = agent.name, agent.email or "", "sí"
        else:
            name, email, registered = key.split(":", 1)[1], "", "no"

        campaigns = sorted({c.campaign_type for c, _ in group if c.campaign_type})
        averages = dimension_averages(group)
        red = sum(1 for _, a in group if (a.global_score or 0) < red_threshold)

        table.append(
            [
                name,
                email,
                " / ".join(campaigns),
                registered,
                len(group),
                average_score(group),
                *[averages.get(k, "") for k in dimension_keys],
                red,
                round(red * 100 / len(group), 1) if group else 0.0,
            ]
        )

    table.sort(key=lambda row: row[5])
    return header, table
