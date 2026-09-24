"""Schemas de llamadas (calls)."""

from datetime import date, datetime

from pydantic import BaseModel

from app.models.call import CallStatus
from app.schemas.analysis import AnalysisOut, TranscriptionOut
from app.schemas.coaching import AcknowledgementOut
from app.schemas.review import ReviewOut


class AgentRef(BaseModel):
    """Referencia ligera a un ejecutivo dentro de una llamada."""

    id: int
    name: str
    campaign: str | None = None

    model_config = {"from_attributes": True}


class CampaignRef(BaseModel):
    """Referencia ligera a la campaña asignada a una llamada."""

    id: int
    name: str

    model_config = {"from_attributes": True}


class CallCreatedOut(BaseModel):
    """Respuesta tras subir una llamada (202 Accepted)."""

    id: int
    status: CallStatus
    agent_id: int | None = None


class BatchCreatedOut(BaseModel):
    """Respuesta tras una subida en lote de llamadas."""

    created_ids: list[int]
    count: int


class AssignAgentRequest(BaseModel):
    """Petición para asignar (o reasignar) una llamada a un ejecutivo."""

    agent_id: int
    # Si es True, asigna también las demás llamadas sin asignar cuyo nombre
    # detectado coincida con el del ejecutivo.
    apply_to_same_name: bool = False


class BulkAssignRequest(BaseModel):
    """Asigna varias llamadas al mismo ejecutivo de una vez."""

    call_ids: list[int]
    agent_id: int


class BulkDeleteRequest(BaseModel):
    """Elimina varias llamadas de una vez."""

    call_ids: list[int]


class BulkResultOut(BaseModel):
    """Resultado de una acción en lote."""

    affected: int
    skipped: int = 0


class ConversationMetricsOut(BaseModel):
    """Métricas deterministas de la conversación (derivadas de los segmentos)."""

    duration_seconds: float | None = None
    agent_talk_seconds: float | None = None
    customer_talk_seconds: float | None = None
    total_speech_seconds: float | None = None
    agent_talk_pct: float | None = None
    customer_talk_pct: float | None = None
    talk_to_listen_ratio: float | None = None
    silence_seconds: float | None = None
    silence_pct: float | None = None
    longest_agent_monologue_seconds: float | None = None
    agent_words_per_minute: float | None = None
    overall_words_per_minute: float | None = None
    turns: int | None = None
    turns_per_minute: float | None = None
    segments_count: int | None = None


class CallStatusOut(BaseModel):
    """Estado del procesamiento de una llamada (para polling)."""

    id: int
    status: CallStatus
    progress_percent: int
    error_message: str | None = None


class CallListItem(BaseModel):
    """Una llamada tal como aparece en el listado paginado."""

    id: int
    # agent es None si la llamada aún no está asignada a un ejecutivo registrado.
    agent: AgentRef | None = None
    detected_agent_name: str | None = None
    call_date: date | None = None
    duration_seconds: int | None = None
    status: CallStatus
    global_score: int | None = None
    # True si la llamada se suspendió por un criterio crítico (auto-fail).
    critical_failed: bool = False
    # Solo en búsquedas (?q=): fragmento de la transcripción con la coincidencia.
    match_snippet: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CallListOut(BaseModel):
    """Listado paginado de llamadas."""

    items: list[CallListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class CallDetailOut(BaseModel):
    """Detalle completo de una llamada: metadata + transcripción + análisis."""

    id: int
    agent: AgentRef | None = None
    detected_agent_name: str | None = None
    responsible: str | None = None
    audio_url: str
    audio_filename: str | None = None
    # Si la política de retención ya borró la grabación: la ficha lo explica en
    # vez de ofrecer un reproductor que va a fallar.
    audio_deleted_at: datetime | None = None
    duration_seconds: int | None = None
    status: CallStatus
    language: str
    call_date: date | None = None
    campaign_type: str | None = None
    campaign_id: int | None = None
    campaign: CampaignRef | None = None
    call_reason: str | None = None
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None
    conversation_metrics: ConversationMetricsOut | None = None
    transcription: TranscriptionOut | None = None
    analysis: AnalysisOut | None = None
    # Revisión humana de la nota, si alguien ya la corrigió. La de la IA
    # (`analysis`) sigue intacta al lado.
    review: ReviewOut | None = None
    # Lo que respondió el asesor a la evaluación, y lo que le contestó el jefe.
    acknowledgement: AcknowledgementOut | None = None

    model_config = {"from_attributes": True}
