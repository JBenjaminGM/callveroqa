"""Endpoints del dashboard: KPIs agregados del equipo, alertas y por ejecutivo."""

import csv
import io
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_manager
from app.models.agent import Agent
from app.models.call import Call
from app.models.user import User
from app.routers.config import read_qa_thresholds
from app.schemas.dashboard import (
    TopicStat,
    AgentDashboardOut,
    AgentPercentileOut,
    AgentRecommendationsOut,
    AgentScore,
    AlertOut,
    CallsByDay,
    CampaignKpiOut,
    ConversationSummary,
    DashboardSummaryOut,
    RecommendationStat,
    ScoreBucket,
    TimelinePoint,
)
from app.services import dashboard_service as ds
from app.services import topic_service
from app.services.name_matching import normalize_name

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def dashboard_summary(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    campaign: str | None = Query(default=None),
    agent_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """KPIs agregados del equipo, con filtros de campaña, ejecutivo y rango de fechas."""
    start, end = ds.resolve_window(period, date_from, date_to)
    thresholds = read_qa_thresholds(db)
    rows = ds.done_analyses(db, start, end=end, agent_id=agent_id, campaign=campaign)

    total_calls = len(rows)
    scores = [a.global_score for _, a in rows]
    average_score = ds.average_score(rows)
    score_trend = ds.format_trend(ds.trend_delta(rows, start, end))

    # Llamadas por día.
    by_day_count: dict[str, int] = defaultdict(int)
    by_day_scores: dict[str, list[int]] = defaultdict(list)
    for call, analysis in rows:
        day = call.created_at.strftime("%Y-%m-%d")
        by_day_count[day] += 1
        by_day_scores[day].append(analysis.global_score)
    calls_by_day = [
        CallsByDay(
            date=day,
            count=by_day_count[day],
            avg_score=round(sum(by_day_scores[day]) / len(by_day_scores[day]), 1),
        )
        for day in sorted(by_day_count)
    ]

    # Distribución de scores en 3 tramos (regla RN-03).
    buckets = {"0-59": 0, "60-79": 0, "80-100": 0}
    for score in scores:
        if score < 60:
            buckets["0-59"] += 1
        elif score < 80:
            buckets["60-79"] += 1
        else:
            buckets["80-100"] += 1
    score_distribution = [ScoreBucket(range=r, count=c) for r, c in buckets.items()]

    agent_avgs = _agent_ranking(db, rows)

    # KPIs de banda roja del equipo.
    red_threshold = thresholds["qa_red_call_threshold"]
    red_count = sum(1 for s in scores if s < red_threshold)
    red_pct = round(red_count / total_calls * 100, 1) if total_calls else 0.0

    conv = ds.conversation_summary(rows)

    return DashboardSummaryOut(
        total_calls=total_calls,
        average_score=average_score,
        score_trend=score_trend,
        calls_by_day=calls_by_day,
        score_distribution=score_distribution,
        top_performers=agent_avgs[:5],
        improvement_opportunities=list(reversed(agent_avgs[-5:])),
        team_dimension_averages=ds.dimension_averages(rows),
        avg_duration_seconds=ds.avg_duration_seconds(rows),
        red_call_count=red_count,
        red_call_pct=red_pct,
        conversation_summary=ConversationSummary(**conv) if conv else None,
    )


def _agent_ranking(db: Session, rows) -> list[AgentScore]:
    """
    Ranking de ejecutivos. Las llamadas asignadas a un ejecutivo registrado se
    agrupan por su id; las que solo tienen nombre detectado por la IA, por ese
    nombre (normalizado).
    """
    by_key: dict[str, list[int]] = defaultdict(list)
    key_meta: dict[str, dict] = {}
    for call, analysis in rows:
        if call.agent_id is not None:
            key = f"a:{call.agent_id}"
            if key not in key_meta:
                agent = db.get(Agent, call.agent_id)
                key_meta[key] = {
                    "agent_id": call.agent_id,
                    "name": agent.name if agent else f"Ejecutivo {call.agent_id}",
                    "registered": True,
                }
        elif call.detected_agent_name:
            key = f"d:{normalize_name(call.detected_agent_name)}"
            if key not in key_meta:
                key_meta[key] = {
                    "agent_id": None,
                    "name": call.detected_agent_name,
                    "registered": False,
                }
        else:
            key = "d:sin-identificar"
            key_meta.setdefault(
                key,
                {"agent_id": None, "name": "Sin identificar", "registered": False},
            )
        by_key[key].append(analysis.global_score)

    agent_avgs: list[AgentScore] = []
    for key, scores_list in by_key.items():
        meta = key_meta[key]
        agent_avgs.append(
            AgentScore(
                agent_id=meta["agent_id"],
                name=meta["name"],
                registered=meta["registered"],
                total_calls=len(scores_list),
                avg_score=round(sum(scores_list) / len(scores_list), 1),
            )
        )
    agent_avgs.sort(key=lambda a: a.avg_score, reverse=True)
    return agent_avgs


@router.get("/campaigns", response_model=list[str])
def list_campaigns(
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Lista las campañas distintas presentes en las llamadas (para los filtros)."""
    rows = db.scalars(
        select(Call.campaign_type)
        .where(Call.campaign_type.is_not(None), Call.campaign_type != "")
        .distinct()
        .order_by(Call.campaign_type)
    ).all()
    return list(rows)


@router.get("/by-campaign", response_model=list[CampaignKpiOut])
def dashboard_by_campaign(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """KPIs por campaña: score + delta vs periodo previo, % rojas, sentimiento, duración."""
    start, end = ds.resolve_window(period, date_from, date_to)
    thresholds = read_qa_thresholds(db)
    data = ds.by_campaign(db, start, end, thresholds["qa_red_call_threshold"])
    return [CampaignKpiOut(**row) for row in data]


@router.get("/report.csv")
def dashboard_report_csv(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    campaign: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Descarga el reporte del equipo en CSV, con los mismos filtros del dashboard."""
    start, end = ds.resolve_window(period, date_from, date_to)
    thresholds = read_qa_thresholds(db)
    header, rows = ds.team_report(
        db, start, end, campaign, thresholds["qa_red_call_threshold"]
    )

    buffer = io.StringIO()
    # BOM UTF-8: sin él, Excel en Windows abre las tildes como caracteres raros.
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)

    filename = f"reporte-equipo-{date.today().isoformat()}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/alerts", response_model=list[AlertOut])
def dashboard_alerts(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Alertas accionables: bajo umbral, caída de tendencia, banda roja, compliance, sentimiento."""
    start, end = ds.resolve_window(period, date_from, date_to)
    thresholds = read_qa_thresholds(db)
    return [AlertOut(**a) for a in ds.build_alerts(db, start, end, thresholds)]


@router.get("/top-recommendations", response_model=list[RecommendationStat])
def dashboard_top_recommendations(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    campaign: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """Problemas recurrentes: agrega las recomendaciones por dimensión/título."""
    start, end = ds.resolve_window(period, date_from, date_to)
    rows = ds.done_analyses(db, start, end=end, campaign=campaign)
    return [RecommendationStat(**r) for r in ds.aggregate_recommendations(rows, limit)]


@router.get("/topics", response_model=list[TopicStat])
def dashboard_topics(
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    campaign: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    """
    Por qué llaman los clientes, con la calidad de cada motivo.

    El resto del panel mide al equipo; esto mide **a qué se enfrenta**. Un motivo
    con mucho volumen y mala nota no es un problema de coaching: es un proceso o
    un producto que hay que arreglar antes.
    """
    start, end = ds.resolve_window(period, date_from, date_to)
    rows = ds.done_analyses(db, start, end=end, campaign=campaign)
    thresholds = read_qa_thresholds(db)
    return [
        TopicStat(**t)
        for t in topic_service.topic_breakdown(
            rows, thresholds["qa_red_call_threshold"], limit
        )
    ]


@router.get("/agents/{agent_id}/percentile", response_model=AgentPercentileOut)
def agent_percentile(
    agent_id: int,
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Percentil ANÓNIMO del asesor dentro de su campaña (oculto bajo el mínimo)."""
    agent = _scoped_agent(db, current_user, agent_id)
    start, end = ds.resolve_window(period, None, None)
    thresholds = read_qa_thresholds(db)
    result = ds.agent_percentile(
        db, agent, start, end, thresholds["qa_min_calls_ranking"]
    )
    return AgentPercentileOut(**result)


@router.get("/agents/{agent_id}/recommendations", response_model=AgentRecommendationsOut)
def agent_recommendations(
    agent_id: int,
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Qué cambiar: recomendaciones agregadas con evidencia + desglose por campaña."""
    agent = _scoped_agent(db, current_user, agent_id)
    start, end = ds.resolve_window(period, None, None)
    return AgentRecommendationsOut(**ds.agent_recommendations(db, agent, start, end))


def _scoped_agent(db: Session, current_user: User, agent_id: int) -> Agent:
    """Valida el scoping (asesor solo lo suyo) y devuelve el ejecutivo o 403/404."""
    if not current_user.is_manager and current_user.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="No autorizado para ver este ejecutivo.")
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Ejecutivo no encontrado.")
    return agent


@router.get("/agents/{agent_id}", response_model=AgentDashboardOut)
def agent_dashboard(
    agent_id: int,
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Performance detallado de un ejecutivo: dimensiones, tendencia y comparativa."""
    agent = _scoped_agent(db, current_user, agent_id)

    start, end = ds.resolve_window(period, None, None)
    agent_rows = ds.done_analyses(db, start, end=end, agent_id=agent_id)
    team_rows = ds.done_analyses(db, start, end=end)

    total_calls = len(agent_rows)
    average_score = ds.average_score(agent_rows)

    dimension_averages = ds.dimension_averages(agent_rows)
    team_dimension_averages = ds.dimension_averages(team_rows)

    # Fortalezas y áreas de mejora: top 3 y bottom 3 dimensiones.
    ordered = sorted(dimension_averages.items(), key=lambda kv: kv[1], reverse=True)
    strengths = [k for k, _ in ordered[:3]]
    improvement_areas = [k for k, _ in ordered[-3:]] if len(ordered) >= 3 else []

    # Tendencia temporal: score promedio por día.
    by_day: dict[str, list[int]] = defaultdict(list)
    for call, analysis in agent_rows:
        by_day[call.created_at.strftime("%Y-%m-%d")].append(analysis.global_score)
    timeline = [
        TimelinePoint(date=day, avg_score=round(sum(v) / len(v), 1))
        for day, v in sorted(by_day.items())
    ]

    score_trend = ds.format_trend(ds.trend_delta(agent_rows, start, end))

    return AgentDashboardOut(
        agent={"id": agent.id, "name": agent.name, "campaign": agent.campaign},
        total_calls=total_calls,
        average_score=average_score,
        score_trend=score_trend,
        dimension_averages=dimension_averages,
        team_dimension_averages=team_dimension_averages,
        strengths=strengths,
        improvement_areas=improvement_areas,
        timeline=timeline,
    )
