"""Schemas del dashboard y reportes agregados."""

from datetime import date

from pydantic import BaseModel


class ConversationSummary(BaseModel):
    """Promedios de las métricas de conversación del periodo."""

    calls_measured: int
    avg_agent_talk_pct: float | None = None
    avg_silence_pct: float | None = None
    avg_talk_to_listen_ratio: float | None = None
    avg_agent_words_per_minute: float | None = None
    avg_longest_monologue_seconds: float | None = None


class CallsByDay(BaseModel):
    """Conteo y score medio de llamadas en un día."""

    date: str
    count: int
    avg_score: float | None = None


class ScoreBucket(BaseModel):
    """Un tramo de la distribución de scores."""

    range: str
    count: int


class AgentScore(BaseModel):
    """
    Score promedio de un ejecutivo en el ranking del dashboard
    (top performers y oportunidades de mejora).

    agent_id es None cuando el ejecutivo fue detectado por la IA pero aún
    no está registrado en el sistema.
    """

    agent_id: int | None = None
    name: str
    avg_score: float
    total_calls: int = 0
    registered: bool = True


class DashboardSummaryOut(BaseModel):
    """KPIs agregados del equipo para el dashboard principal."""

    total_calls: int
    average_score: float
    score_trend: str
    calls_by_day: list[CallsByDay]
    score_distribution: list[ScoreBucket]
    top_performers: list[AgentScore]
    improvement_opportunities: list[AgentScore]
    # --- Fase 2: dimensiones del equipo, duración media y conversación ---
    team_dimension_averages: dict[str, float] = {}
    avg_duration_seconds: float | None = None
    red_call_count: int = 0
    red_call_pct: float = 0.0
    conversation_summary: ConversationSummary | None = None


class CampaignKpiOut(BaseModel):
    """KPIs de una campaña con su delta vs el periodo anterior."""

    campaign: str
    total_calls: int
    avg_score: float
    score_delta: float | None = None
    red_calls: int
    red_pct: float
    # Suspendidas por criterio crítico (auto-fail): riesgo normativo de la campaña.
    critical_calls: int = 0
    critical_pct: float = 0.0
    sentiment: float | None = None
    avg_duration_seconds: float | None = None


class AlertOut(BaseModel):
    """Una alerta accionable del dashboard del jefe."""

    type: str
    severity: str            # high | medium | low
    title: str
    description: str
    campaign: str | None = None
    agent_id: int | None = None
    agent_name: str | None = None
    call_id: int | None = None
    value: float | None = None


class RecommendationStat(BaseModel):
    """Una recomendación recurrente agregada (problema del equipo)."""

    dimension: str
    title: str
    count: int
    priority: str
    sample_description: str = ""


class AgentRecommendationStat(RecommendationStat):
    """Recomendación agregada del asesor, con evidencia de un segmento real."""

    evidence: str | None = None


class AgentCampaignBreakdown(BaseModel):
    """Desempeño del asesor en una campaña + cumplimiento de la nota de producto."""

    campaign: str
    total_calls: int
    avg_score: float
    compliance: dict | None = None


class AgentPercentileOut(BaseModel):
    """Percentil anónimo del asesor dentro de su campaña."""

    available: bool
    campaign: str | None = None
    peers_count: int
    percentile: int | None = None
    agent_avg: float | None = None
    campaign_avg: float | None = None
    rank: int | None = None


class AgentRecommendationsOut(BaseModel):
    """Recomendaciones agregadas del asesor + desglose por campaña."""

    total_calls: int
    recommendations: list[AgentRecommendationStat]
    by_campaign: list[AgentCampaignBreakdown]


class TimelinePoint(BaseModel):
    """Un punto de la evolución temporal de un ejecutivo."""

    date: str
    avg_score: float


class AgentDashboardOut(BaseModel):
    """Performance detallado de un ejecutivo."""

    agent: dict
    total_calls: int
    average_score: float
    score_trend: str
    dimension_averages: dict[str, float]
    team_dimension_averages: dict[str, float]
    strengths: list[str]
    improvement_areas: list[str]
    timeline: list[TimelinePoint]


class TopicStat(BaseModel):
    """Un motivo de llamada con su volumen y su calidad."""

    topic: str
    total_calls: int
    avg_score: float
    red_calls: int
    red_pct: float
    critical_calls: int = 0


# ------------------------- Suspendidas por criterio crítico -------------------------


class CriticalWeekOut(BaseModel):
    week_start: date
    total_calls: int
    critical_calls: int
    critical_pct: float


class CriticalAgentOut(BaseModel):
    agent_id: int
    agent_name: str
    total_calls: int
    critical_calls: int
    critical_pct: float
    # Tasa en cada mitad del periodo; nula con pocas llamadas en una de ellas.
    first_half_pct: float | None = None
    second_half_pct: float | None = None
    top_criterion: str | None = None


class CriticalCriterionOut(BaseModel):
    criterion: str
    count: int


class CriticalReportOut(BaseModel):
    """Suspendidas del periodo: total, serie semanal, por asesor y por criterio."""

    total_calls: int
    critical_calls: int
    critical_pct: float
    first_half_pct: float | None = None
    second_half_pct: float | None = None
    weekly: list[CriticalWeekOut]
    by_agent: list[CriticalAgentOut]
    top_criteria: list[CriticalCriterionOut]
