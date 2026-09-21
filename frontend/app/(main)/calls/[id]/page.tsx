'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Download,
  RefreshCw,
  Trash2,
  UserPlus,
} from 'lucide-react';
import {
  useAgents,
  useAssignCall,
  useCall,
  useDeleteCall,
  useRetryCall,
} from '@/lib/queries';
import { api, getErrorMessage } from '@/lib/api';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import {
  TranscriptPlayer,
  type TranscriptPlayerHandle,
} from '@/components/calls/transcript-player';
import {
  CriticalFailuresCard,
  EvidenceChips,
} from '@/components/calls/evidence';
import { ReviewCard } from '@/components/calibration/review-card';
import { AcknowledgementCard } from '@/components/coaching/acknowledgement-card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { PriorityBadge, ScoreBadge, StatusBadge } from '@/components/ui/badge';
import { Spinner, ErrorState, Skeleton } from '@/components/ui/feedback';
import { ScoreRadar } from '@/components/charts/score-radar';
import { ConversationMetricsCard } from '@/components/dashboard/insights';
import { ScoreGauge } from '@/components/dashboard/viz';
import type { CallDetail } from '@/types';
import {
  callAgentName,
  dimensionLabel,
  formatDate,
  formatDateTime,
  formatDuration,
  scoreColor,
  scoreLabel,
  STATUS_LABELS,
} from '@/lib/utils';

/** Detalle completo de una llamada: estado, scores, recomendaciones y transcripción. */
export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const { data: call, isLoading, error, refetch, isFetching } = useCall(id, true);
  const retry = useRetryCall();
  const remove = useDeleteCall();
  const [downloading, setDownloading] = useState(false);
  const playerRef = useRef<TranscriptPlayerHandle>(null);
  const jumpTo = (index: number) => playerRef.current?.jumpToSegment(index);
  const transcriptSegments = call?.transcription?.segments ?? [];

  const processing =
    call && call.status !== 'DONE' && call.status !== 'ERROR';

  async function downloadPdf() {
    setDownloading(true);
    try {
      const res = await api.get(`/calls/${id}/report.pdf`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte_llamada_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(getErrorMessage(err));
    } finally {
      setDownloading(false);
    }
  }

  async function onDelete() {
    if (!confirm('¿Eliminar esta llamada? Esta acción no se puede deshacer.')) {
      return;
    }
    await remove.mutateAsync(id);
    router.push('/calls');
  }

  return (
    <>
      <Header title={`Llamada #${id}`} />
      <main className="flex-1 overflow-y-auto p-6">
        <button
          onClick={() => router.push('/calls')}
          className="mb-4 flex items-center gap-1.5 text-small text-text-secondary
                     transition-colors hover:text-accent-primary"
        >
          <ArrowLeft size={16} />
          Volver al listado
        </button>

        {isLoading && (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-28" />
            <Skeleton className="h-64" />
          </div>
        )}

        {error && <ErrorState message={getErrorMessage(error)} />}

        {call && (
          <div className="flex flex-col gap-6">
            {/* Cabecera de la llamada */}
            <Card className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="flex items-center gap-2 text-h3 text-text-primary">
                  {callAgentName(call)}
                  {!call.agent && call.detected_agent_name && (
                    <span
                      className="rounded-control bg-warning/15 px-2 py-0.5
                                 text-small font-medium text-warning"
                    >
                      Detectado por IA · sin registrar
                    </span>
                  )}
                </p>
                <p className="text-small text-text-secondary">
                  {call.campaign ? (
                    <Link
                      href={`/campaigns/${call.campaign.id}`}
                      className="hover:text-accent-primary"
                    >
                      {call.campaign.name}
                    </Link>
                  ) : (
                    call.campaign_type ?? call.agent?.campaign ?? 'Sin campaña'
                  )}
                  {' · '}
                  Subida {formatDate(call.created_at)}
                  {' · '}
                  {formatDuration(call.duration_seconds)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={call.status} />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetch()}
                  disabled={isFetching}
                  title="Actualizar estado"
                >
                  <RefreshCw
                    size={16}
                    className={isFetching ? 'animate-spin' : undefined}
                  />
                  Actualizar
                </Button>
                {call.status === 'ERROR' && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => retry.mutate(id)}
                    disabled={retry.isPending}
                  >
                    <RefreshCw size={16} />
                    Reintentar
                  </Button>
                )}
                {call.status === 'DONE' && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={downloadPdf}
                    disabled={downloading}
                  >
                    {downloading ? <Spinner /> : <Download size={16} />}
                    Reporte PDF
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onDelete}
                  disabled={remove.isPending}
                >
                  <Trash2 size={16} />
                </Button>
              </div>
            </Card>

            {/* Asignación de ejecutivo (si la IA detectó un nombre sin registrar) */}
            {!call.agent && call.detected_agent_name && (
              <AssignAgentCard call={call} />
            )}

            {/* Estado de procesamiento */}
            {processing && (
              <Card className="flex items-center gap-3">
                <Spinner className="h-5 w-5 text-accent-primary" />
                <span className="text-body text-text-primary">
                  Procesando: {STATUS_LABELS[call.status]}… La página se
                  actualiza automáticamente.
                </span>
              </Card>
            )}

            {/* Error de procesamiento */}
            {call.status === 'ERROR' && (
              <ErrorState
                message={
                  call.error_message ??
                  'La llamada no pudo procesarse. Inténtalo de nuevo.'
                }
              />
            )}

            {/* Análisis */}
            {call.analysis && (
              <>
                {!!call.analysis.critical_failures?.length && (
                  <CriticalFailuresCard
                    failures={call.analysis.critical_failures}
                    uncappedScore={call.analysis.uncapped_score}
                    transcriptSegments={transcriptSegments}
                    onJump={jumpTo}
                  />
                )}

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  <Card className="flex flex-col items-center justify-center gap-3">
                    <span className="destacado text-[11px] text-text-muted">
                      score global
                    </span>
                    <ScoreGauge
                      value={call.analysis.global_score}
                      decimals={0}
                      label="sobre 100"
                    />
                    <ScoreBadge score={call.analysis.global_score} showLabel />
                  </Card>

                  <Card className="lg:col-span-2">
                    <CardTitle className="mb-2">
                      Comparativa por dimensión
                    </CardTitle>
                    <ScoreRadar
                      scores={call.analysis.dimension_scores}
                      teamScores={call.analysis.team_average}
                    />
                  </Card>
                </div>

                <Card>
                  <CardTitle className="mb-1">Scores por dimensión</CardTitle>
                  <p className="mb-4 text-small text-text-muted">
                    {call.analysis.dimension_evidence
                      ? 'Cada nota con su porqué. Pulsa un tiempo para escuchar ese momento.'
                      : 'Análisis anterior a la evidencia por nota: reprocesa la llamada para obtenerla.'}
                  </p>
                  <div className="flex flex-col gap-4">
                    {Object.entries(call.analysis.dimension_scores).map(
                      ([key, score]) => {
                        const evidence = call.analysis?.dimension_evidence?.[key];
                        return (
                          <div key={key}>
                            <div className="mb-1 flex justify-between text-small">
                              <span className="text-text-primary">
                                {dimensionLabel(key)}
                              </span>
                              <span
                                className="font-semibold"
                                style={{ color: scoreColor(score) }}
                              >
                                {score} · {scoreLabel(score)}
                              </span>
                            </div>
                            <div className="h-2.5 w-full overflow-hidden rounded-full bg-bg-accent">
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${score}%`,
                                  background: scoreColor(score),
                                }}
                              />
                            </div>
                            {evidence && (
                              <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
                                {evidence.justification && (
                                  <span className="text-small text-text-secondary">
                                    {evidence.justification}
                                  </span>
                                )}
                                <EvidenceChips
                                  segments={evidence.segments}
                                  transcriptSegments={transcriptSegments}
                                  onJump={jumpTo}
                                />
                              </div>
                            )}
                          </div>
                        );
                      },
                    )}
                  </div>
                </Card>

                {call.analysis.summary && (
                  <Card>
                    <CardTitle className="mb-2">Resumen</CardTitle>
                    <p className="text-body text-text-secondary">
                      {call.analysis.summary}
                    </p>
                  </Card>
                )}

                {call.analysis.recommendations.length > 0 && (
                  <Card>
                    <CardTitle className="mb-3">
                      Recomendaciones accionables
                    </CardTitle>
                    <div className="flex flex-col gap-3">
                      {call.analysis.recommendations.map((rec, i) => (
                        <div
                          key={i}
                          className="rounded-card bg-bg-secondary p-3"
                        >
                          <div className="mb-1 flex items-center gap-2">
                            <PriorityBadge priority={rec.priority} />
                            <span className="text-body font-semibold text-text-primary">
                              {rec.title}
                            </span>
                          </div>
                          <p className="text-small text-text-secondary">
                            {rec.description}
                          </p>
                          <p className="mt-1 text-small text-text-muted">
                            Dimensión: {dimensionLabel(rec.dimension)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </>
            )}

            {/* Revisión humana de la nota (no sustituye a la de la IA) */}
            {call.analysis && <ReviewCard call={call} />}

            {/* La conversación sobre la evaluación: asesor y jefe */}
            {call.analysis && <AcknowledgementCard call={call} />}

            {/* Dinámica de la conversación (métricas deterministas) */}
            {call.conversation_metrics && (
              <ConversationMetricsCard metrics={call.conversation_metrics} />
            )}

            {/* Transcripción sincronizada con el audio */}
            {call.transcription && (
              <TranscriptPlayer
                ref={playerRef}
                callId={call.id}
                transcription={call.transcription}
                audioFilename={call.audio_filename}
              />
            )}

            <p className="text-small text-text-muted">
              Subida el {formatDateTime(call.created_at)}
              {call.responsible && ` · Responsable: ${call.responsible}`}
              {call.processed_at &&
                ` · Procesada el ${formatDateTime(call.processed_at)}`}
            </p>
          </div>
        )}
      </main>
    </>
  );
}

/**
 * Tarjeta para asignar la llamada a un ejecutivo registrado cuando la IA
 * detectó un nombre que no está en la base de datos.
 */
function AssignAgentCard({ call }: { call: CallDetail }) {
  const { data: agents } = useAgents({ active: true });
  const assign = useAssignCall();
  const [agentId, setAgentId] = useState('');
  const [applyAll, setApplyAll] = useState(true);

  async function onAssign() {
    if (!agentId) return;
    await assign.mutateAsync({
      id: call.id,
      agentId: Number(agentId),
      applyToSameName: applyAll,
    });
  }

  return (
    <Card className="ring-1 ring-warning/40">
      <CardTitle className="mb-1 flex items-center gap-2">
        <UserPlus size={18} className="text-warning" />
        Ejecutivo detectado sin registrar
      </CardTitle>
      <p className="mb-4 text-small text-text-secondary">
        La IA identificó a{' '}
        <strong className="text-text-primary">
          {call.detected_agent_name}
        </strong>{' '}
        en la llamada, pero no está registrado. Asígnalo a un ejecutivo
        existente o créalo primero en la sección Ejecutivos.
      </p>

      <div className="flex flex-wrap items-end gap-3">
        <div className="w-60">
          <label className="mb-1.5 block text-small text-text-secondary">
            Asignar a ejecutivo registrado
          </label>
          <Select value={agentId} onChange={(e) => setAgentId(e.target.value)}>
            <option value="">Selecciona un ejecutivo…</option>
            {agents?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        </div>
        <Button onClick={onAssign} disabled={!agentId || assign.isPending}>
          {assign.isPending ? <Spinner /> : <UserPlus size={16} />}
          Asignar
        </Button>
        <Link href="/agents">
          <Button variant="ghost">Crear ejecutivo</Button>
        </Link>
      </div>

      <label className="mt-3 flex items-center gap-2 text-small text-text-secondary">
        <input
          type="checkbox"
          checked={applyAll}
          onChange={(e) => setApplyAll(e.target.checked)}
          className="accent-[var(--accent-primary)]"
        />
        Asignar también las demás llamadas con este mismo nombre detectado
      </label>
    </Card>
  );
}
