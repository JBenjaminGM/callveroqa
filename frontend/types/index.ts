/** Tipos TypeScript que reflejan los contratos de la API del backend. */

export type CallStatus =
  | 'QUEUED'
  | 'TRANSCRIBING'
  | 'ANALYZING'
  | 'DONE'
  | 'ERROR';

export type Role = 'admin' | 'jefe' | 'asesor';

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role | string;
  /** Vínculo del asesor a su ficha de ejecutivo (null para admin/jefe). */
  agent_id?: number | null;
  last_login?: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Agent {
  id: number;
  name: string;
  email?: string | null;
  campaign?: string | null;
  start_date?: string | null;
  photo_url?: string | null;
  active: boolean;
}

export interface AgentDetail extends Agent {
  total_calls: number;
  average_score?: number | null;
}

export interface AgentRef {
  id: number;
  name: string;
  campaign?: string | null;
}

export interface CampaignRef {
  id: number;
  name: string;
}

export interface Campaign {
  id: number;
  name: string;
  product_service?: string | null;
  offer_description?: string | null;
  key_benefits: string[];
  pricing_conditions?: string | null;
  customer_requirements?: string | null;
  mandatory_phrases: string[];
  prohibited_claims: string[];
  target_audience?: string | null;
  additional_notes?: string | null;
  source: string;
  source_filename?: string | null;
  active: boolean;
  created_at: string;
  calls_count?: number;
}

/** Borrador de nota de producto (todos los campos opcionales). */
export interface CampaignDraft {
  name?: string | null;
  product_service?: string | null;
  offer_description?: string | null;
  key_benefits?: string[] | null;
  pricing_conditions?: string | null;
  customer_requirements?: string | null;
  mandatory_phrases?: string[] | null;
  prohibited_claims?: string[] | null;
  target_audience?: string | null;
  additional_notes?: string | null;
}

export interface CampaignExtractResult {
  draft: CampaignDraft;
  missing_fields: string[];
  source_filename?: string | null;
  warning?: string | null;
}

export interface CampaignAssistResult {
  draft: CampaignDraft;
  warning?: string | null;
}

export interface Recommendation {
  priority: 'high' | 'medium' | 'low';
  dimension: string;
  title: string;
  description: string;
}

export interface TranscriptionSegment {
  start: number;
  end: number;
  speaker: string;
  text: string;
}

/** Métricas deterministas de la conversación (derivadas de los segmentos). */
export interface ConversationMetrics {
  duration_seconds?: number | null;
  agent_talk_seconds?: number | null;
  customer_talk_seconds?: number | null;
  total_speech_seconds?: number | null;
  agent_talk_pct?: number | null;
  customer_talk_pct?: number | null;
  talk_to_listen_ratio?: number | null;
  silence_seconds?: number | null;
  silence_pct?: number | null;
  longest_agent_monologue_seconds?: number | null;
  agent_words_per_minute?: number | null;
  overall_words_per_minute?: number | null;
  turns?: number | null;
  turns_per_minute?: number | null;
  segments_count?: number | null;
}

export interface Transcription {
  full_text: string;
  segments: TranscriptionSegment[];
  language?: string | null;
}

/** Por qué la IA puso una nota y en qué segmentos (índices) se apoya. */
export interface DimensionEvidence {
  justification: string;
  segments: number[];
}

/** Un criterio crítico (auto-fail) incumplido: suspende la llamada. */
export interface CriticalFailure {
  dimension: string;
  criterion: string;
  segment?: number | null;
  reason: string;
}

export interface Analysis {
  global_score: number;
  dimension_scores: Record<string, number>;
  /** Nulo en análisis anteriores a que existiera la evidencia. */
  dimension_evidence?: Record<string, DimensionEvidence> | null;
  critical_failures?: CriticalFailure[] | null;
  /** Nota que habría tenido sin el auto-fail (solo si hay fallos críticos). */
  uncapped_score?: number | null;
  recommendations: Recommendation[];
  summary?: string | null;
  ai_provider?: string | null;
  ai_model?: string | null;
  team_average?: Record<string, number> | null;
}

export interface CallListItem {
  id: number;
  /** null si la llamada aún no está asignada a un ejecutivo registrado. */
  agent?: AgentRef | null;
  detected_agent_name?: string | null;
  call_date?: string | null;
  duration_seconds?: number | null;
  status: CallStatus;
  global_score?: number | null;
  /** Suspendida por un criterio crítico (auto-fail). */
  critical_failed?: boolean;
  /** Solo en búsquedas: fragmento de la transcripción que coincide. */
  match_snippet?: string | null;
  created_at: string;
}

export interface CallList {
  items: CallListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CallDetail {
  id: number;
  agent?: AgentRef | null;
  detected_agent_name?: string | null;
  responsible?: string | null;
  audio_url: string;
  audio_filename?: string | null;
  /** Cuándo borró la política de retención la grabación (la nota se conserva). */
  audio_deleted_at?: string | null;
  duration_seconds?: number | null;
  status: CallStatus;
  language: string;
  call_date?: string | null;
  campaign_type?: string | null;
  campaign_id?: number | null;
  campaign?: CampaignRef | null;
  call_reason?: string | null;
  error_message?: string | null;
  created_at: string;
  processed_at?: string | null;
  conversation_metrics?: ConversationMetrics | null;
  transcription?: Transcription | null;
  analysis?: Analysis | null;
  /** Revisión humana de la nota. Convive con `analysis`, no lo reemplaza. */
  review?: Review | null;
  /** Lo que respondió el asesor a la evaluación, y lo que le contestó el jefe. */
  acknowledgement?: Acknowledgement | null;
}

/* ----------------------------- Calibración ----------------------------- */

/** Puntuación humana de una llamada, con la de la IA al lado para comparar. */
export interface Review {
  id: number;
  call_id: number;
  reviewer_id?: number | null;
  reviewer_name?: string | null;
  global_score: number;
  dimension_scores: Record<string, number>;
  comment?: string | null;
  /** True si se puntuó sin ver la nota de la IA (sesión de calibración). */
  blind: boolean;
  created_at: string;
  updated_at?: string | null;
  ai_global_score?: number | null;
  ai_dimension_scores?: Record<string, number> | null;
  /** Diferencia humano − IA. */
  global_delta?: number | null;
  dimension_deltas?: Record<string, number> | null;
}

/** Lo que se envía al guardar una revisión. El global lo calcula el backend. */
export interface ReviewInput {
  dimension_scores: Record<string, number>;
  comment?: string | null;
  blind?: boolean;
}

/** Una llamada pendiente de calibrar. */
export interface CalibrationCall {
  id: number;
  agent_name?: string | null;
  campaign?: string | null;
  call_date?: string | null;
  duration_seconds?: number | null;
  created_at: string;
}

/**
 * Una llamada para puntuar a ciegas. No trae el análisis de la IA: el score
 * no llega al navegador, así la sesión es ciega de verdad.
 */
export interface BlindCall {
  id: number;
  agent_name?: string | null;
  campaign?: string | null;
  call_date?: string | null;
  duration_seconds?: number | null;
  audio_filename?: string | null;
  transcription?: Transcription | null;
}

/** Acuerdo IA-humano en una dimensión concreta. */
export interface DimensionAgreement {
  dimension_key: string;
  dimension_name: string;
  count: number;
  human_avg?: number | null;
  ai_avg?: number | null;
  /** Sesgo (humano − IA): negativo = la IA puntúa más alto. */
  bias?: number | null;
  /** Desviación media absoluta: cuánto se separan sin cancelarse. */
  mean_abs_diff: number;
  agreement_pct?: number | null;
}

export interface Agreement {
  reviews_count: number;
  blind_only: boolean;
  tolerance: number;
  human_avg?: number | null;
  ai_avg?: number | null;
  bias?: number | null;
  mean_abs_diff: number;
  agreement_pct?: number | null;
  dimensions: DimensionAgreement[];
  worst_dimension?: string | null;
}

/* ------------------------- Cierre del ciclo ---------------------------- */

/** Lo que el asesor responde a la evaluación de una de sus llamadas. */
export interface Acknowledgement {
  id: number;
  call_id: number;
  user_id?: number | null;
  user_name?: string | null;
  comment?: string | null;
  review_requested: boolean;
  manager_reply?: string | null;
  replied_by_name?: string | null;
  replied_at?: string | null;
  created_at: string;
  updated_at?: string | null;
  /** True mientras pidió revisión y nadie ha contestado. */
  pending_review: boolean;
}

export interface AcknowledgementInput {
  comment?: string | null;
  review_requested?: boolean;
}

/** Una llamada que merece escucharse, con el motivo por el que sale. */
export interface ListenSuggestion {
  call_id: number;
  agent_id?: number | null;
  agent_name?: string | null;
  campaign?: string | null;
  score?: number | null;
  call_date?: string | null;
  reason:
    | 'review_requested'
    | 'critical_failed'
    | 'red_unreviewed'
    | 'below_own_average'
    | 'never_reviewed_agent'
    | string;
  priority: 'high' | 'medium' | 'low' | string;
  title: string;
  description: string;
}

/** Una evaluación de la que el asesor todavía no ha acusado recibo. */
export interface PendingCall {
  call_id: number;
  global_score: number;
  call_date?: string | null;
  campaign?: string | null;
  created_at: string;
}

export interface CallStatusInfo {
  id: number;
  status: CallStatus;
  progress_percent: number;
  error_message?: string | null;
}

export interface AgentScore {
  /** null cuando el ejecutivo fue detectado por la IA pero no está registrado. */
  agent_id?: number | null;
  name: string;
  avg_score: number;
  total_calls: number;
  registered: boolean;
}

export interface ConversationSummary {
  calls_measured: number;
  avg_agent_talk_pct?: number | null;
  avg_silence_pct?: number | null;
  avg_talk_to_listen_ratio?: number | null;
  avg_agent_words_per_minute?: number | null;
  avg_longest_monologue_seconds?: number | null;
}

export interface DashboardSummary {
  total_calls: number;
  average_score: number;
  score_trend: string;
  calls_by_day: { date: string; count: number; avg_score?: number | null }[];
  score_distribution: { range: string; count: number }[];
  top_performers: AgentScore[];
  improvement_opportunities: AgentScore[];
  // --- Fase 2 ---
  team_dimension_averages: Record<string, number>;
  avg_duration_seconds?: number | null;
  red_call_count: number;
  red_call_pct: number;
  conversation_summary?: ConversationSummary | null;
}

/** KPIs de una campaña con delta vs el periodo anterior. */
export interface CampaignKpi {
  campaign: string;
  total_calls: number;
  avg_score: number;
  score_delta?: number | null;
  red_calls: number;
  red_pct: number;
  /** Suspendidas por criterio crítico (auto-fail). */
  critical_calls: number;
  critical_pct: number;
  sentiment?: number | null;
  avg_duration_seconds?: number | null;
}

/** Una alerta accionable del dashboard del jefe. */
export interface DashboardAlert {
  type: string;
  severity: 'high' | 'medium' | 'low' | string;
  title: string;
  description: string;
  campaign?: string | null;
  agent_id?: number | null;
  agent_name?: string | null;
  call_id?: number | null;
  value?: number | null;
}

/** Una recomendación recurrente agregada (problema del equipo). */
export interface RecommendationStat {
  dimension: string;
  title: string;
  count: number;
  priority: string;
  sample_description: string;
}

/** Recomendación agregada del asesor con evidencia de un segmento real. */
export interface AgentRecommendationStat extends RecommendationStat {
  evidence?: string | null;
}

export interface ProductNoteCompliance {
  calls_measured: number;
  coverage_pct?: number | null;
  prohibited_hits: number;
  mandatory_missing: string[];
}

export interface AgentCampaignBreakdown {
  campaign: string;
  total_calls: number;
  avg_score: number;
  compliance?: ProductNoteCompliance | null;
}

export interface AgentPercentile {
  available: boolean;
  campaign?: string | null;
  peers_count: number;
  percentile?: number | null;
  agent_avg?: number | null;
  campaign_avg?: number | null;
  rank?: number | null;
}

export interface AgentRecommendations {
  total_calls: number;
  recommendations: AgentRecommendationStat[];
  by_campaign: AgentCampaignBreakdown[];
}

export interface AgentDashboard {
  agent: { id: number; name: string; campaign?: string | null };
  total_calls: number;
  average_score: number;
  score_trend: string;
  dimension_averages: Record<string, number>;
  team_dimension_averages: Record<string, number>;
  strengths: string[];
  improvement_areas: string[];
  timeline: { date: string; avg_score: number }[];
}

export interface RubricCriterion {
  name: string;
  enabled: boolean;
  /** Crítico (auto-fail): incumplirlo suspende la llamada entera. */
  critical?: boolean;
}

export interface RubricDimension {
  dimension_key: string;
  dimension_name: string;
  description?: string | null;
  weight: number;
  display_order?: number | null;
  criteria: RubricCriterion[];
}

/** Forma enviada al guardar la rúbrica (dimension_key vacío = categoría nueva). */
export interface RubricDimensionInput {
  dimension_key?: string;
  dimension_name: string;
  description?: string | null;
  weight: number;
  criteria: RubricCriterion[];
}

export interface AppSettings {
  default_language: string;
  ai_provider: string;
  whisper_provider: string;
  // Umbrales / metas de QA configurables.
  qa_target_score?: number;
  qa_low_agent_threshold?: number;
  qa_red_call_threshold?: number;
  qa_min_calls_ranking?: number;
  qa_trend_drop_alert?: number;
  /** Días que se conservan las grabaciones. 0 = no caducan. */
  retention_audio_days?: number;
}

/** Una cuenta tal como la ve un administrador en la pantalla de usuarios. */
export interface AccountUser {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'jefe' | 'asesor' | string;
  agent_id?: number | null;
  active: boolean;
  is_readonly: boolean;
  created_at?: string | null;
  last_login?: string | null;
}

/** Alta de cuenta: la contraseña generada solo viaja en esta respuesta. */
export interface CreatedUser {
  user: AccountUser;
  generated_password?: string | null;
}

/** Un motivo de llamada con su volumen y su calidad. */
export interface TopicStat {
  topic: string;
  total_calls: number;
  avg_score: number;
  red_calls: number;
  red_pct: number;
  critical_calls: number;
}
