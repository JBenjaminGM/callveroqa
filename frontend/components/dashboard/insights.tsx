'use client';

import Link from 'next/link';
import {
  AlertTriangle,
  Award,
  CheckCircle2,
  ChevronRight,
  Clock,
  Frown,
  Gauge,
  MessageSquare,
  Mic,
  OctagonX,
  Repeat,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  UserMinus,
  Volume2,
} from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/card';
import { PriorityBadge, ScoreBadge } from '@/components/ui/badge';
import { ScoreRadar } from '@/components/charts/score-radar';
import { DeltaPill, Donut, MiniProgress, scoreVar } from '@/components/dashboard/viz';
import { dimensionLabel, formatDuration } from '@/lib/utils';
import type {
  AgentCampaignBreakdown,
  AgentPercentile,
  AgentRecommendationStat,
  CampaignKpi,
  ConversationMetrics,
  ConversationSummary,
  DashboardAlert,
  RecommendationStat,
} from '@/types';

/* --------------------------------------------------------------------------- *
 * Alertas accionables — franja de severidad + icono por tipo + enlace
 * --------------------------------------------------------------------------- */
const ALERT_META: Record<
  string,
  { color: string; icon: typeof AlertTriangle; tone: string }
> = {
  critical_failure: { color: 'var(--danger)', icon: OctagonX, tone: 'suspendida' },
  red_call: { color: 'var(--danger)', icon: AlertTriangle, tone: 'banda roja' },
  low_agent: { color: 'var(--warning)', icon: UserMinus, tone: 'bajo umbral' },
  trend_drop: { color: 'var(--warning)', icon: TrendingDown, tone: 'tendencia' },
  prohibited_claim: { color: 'var(--danger)', icon: ShieldAlert, tone: 'compliance' },
  compliance_breach: { color: 'var(--warning)', icon: ShieldAlert, tone: 'compliance' },
  sentiment_anomaly: { color: 'var(--info)', icon: Frown, tone: 'sentimiento' },
};
const SEV_COLOR: Record<string, string> = {
  high: 'var(--danger)',
  medium: 'var(--warning)',
  low: 'var(--info)',
};

export function AlertsPanel({ alerts }: { alerts: DashboardAlert[] }) {
  if (alerts.length === 0) {
    return (
      <Card className="flex items-center gap-3">
        <CheckCircle2 size={22} className="shrink-0 text-success" />
        <div>
          <p className="text-body font-semibold text-text-primary">
            Todo en orden
          </p>
          <p className="text-small text-text-secondary">
            Sin alertas en este periodo. El equipo está dentro de los umbrales.
          </p>
        </div>
      </Card>
    );
  }
  const high = alerts.filter((a) => a.severity === 'high').length;
  return (
    <Card className="p-0">
      <div className="flex items-center justify-between px-5 pt-5">
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle size={18} className="text-warning" />
          Alertas <span className="hl">accionables</span>
        </CardTitle>
        <div className="flex items-center gap-2">
          {high > 0 && (
            <span className="rounded-control bg-danger/12 px-2.5 py-1 text-small font-bold text-danger">
              {high} críticas
            </span>
          )}
          <span className="rounded-control bg-bg-accent px-2.5 py-1 text-small font-semibold text-text-secondary">
            {alerts.length}
          </span>
        </div>
      </div>
      <ul className="mt-2 flex max-h-[26rem] flex-col overflow-y-auto px-2 pb-2">
        {alerts.map((a, i) => {
          const meta = ALERT_META[a.type] ?? {
            color: SEV_COLOR[a.severity] ?? 'var(--info)',
            icon: AlertTriangle,
            tone: a.type,
          };
          const Icon = meta.icon;
          const href = a.call_id
            ? `/calls/${a.call_id}`
            : a.agent_id
              ? `/agents/${a.agent_id}`
              : undefined;
          const body = (
            <div className="flex items-center gap-3 rounded-card px-3 py-2.5 transition-colors hover:bg-bg-accent/50">
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control"
                style={{ background: `color-mix(in srgb, ${meta.color} 14%, transparent)`, color: meta.color }}
              >
                <Icon size={17} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-body font-medium text-text-primary">
                  {a.title}
                </p>
                <p className="truncate text-small text-text-secondary">
                  {a.description}
                </p>
              </div>
              {href && <ChevronRight size={16} className="shrink-0 text-text-muted" />}
            </div>
          );
          return (
            <li
              key={i}
              className="border-l"
              style={{ borderColor: SEV_COLOR[a.severity] ?? 'var(--info)' }}
            >
              {href ? <Link href={href}>{body}</Link> : body}
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * KPIs por campaña — tabla con barras inline + delta chips
 * --------------------------------------------------------------------------- */
export function CampaignKpiTable({ rows }: { rows: CampaignKpi[] }) {
  if (rows.length === 0) {
    return (
      <Card>
        <CardTitle className="mb-2">Rendimiento por <span className="hl">campaña</span></CardTitle>
        <p className="text-small text-text-muted">Sin datos en este periodo.</p>
      </Card>
    );
  }
  return (
    <Card>
      <CardTitle className="mb-4">Rendimiento por <span className="hl">campaña</span></CardTitle>
      <div className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-y-1 text-small">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wide text-text-muted">
              <th className="pb-1 pr-3 font-semibold">Campaña</th>
              <th className="pb-1 pr-3 font-semibold">Vol.</th>
              <th className="w-[34%] pb-1 pr-3 font-semibold">Score QA</th>
              <th className="pb-1 pr-3 font-semibold">Δ</th>
              <th className="pb-1 pr-3 font-semibold">% rojas</th>
              <th className="pb-1 pr-3 font-semibold">Suspend.</th>
              <th className="pb-1 font-semibold">Sentim.</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.campaign} className="group">
                <td className="max-w-[10rem] truncate py-1.5 pr-3 font-medium text-text-primary">
                  {r.campaign}
                </td>
                <td className="py-1.5 pr-3 font-mono tabular-nums text-text-secondary">
                  {r.total_calls}
                </td>
                <td className="py-1.5 pr-3">
                  <div className="flex items-center gap-2">
                    <div className="min-w-[70px] flex-1">
                      <MiniProgress value={r.avg_score} />
                    </div>
                    <span
                      className="w-9 shrink-0 text-right font-mono font-semibold tabular-nums"
                      style={{ color: scoreVar(r.avg_score) }}
                    >
                      {r.avg_score.toFixed(0)}
                    </span>
                  </div>
                </td>
                <td className="py-1.5 pr-3">
                  <DeltaPill delta={r.score_delta} size="xs" />
                </td>
                <td className="py-1.5 pr-3">
                  <span
                    className="font-mono font-semibold tabular-nums"
                    style={{ color: r.red_pct > 25 ? 'var(--danger)' : 'var(--text-secondary)' }}
                  >
                    {r.red_pct}%
                  </span>
                </td>
                <td className="py-1.5 pr-3">
                  {r.critical_calls > 0 ? (
                    <span
                      className="inline-flex items-center gap-1 font-mono font-semibold tabular-nums"
                      style={{ color: 'var(--danger)' }}
                      title={`${r.critical_calls} llamada(s) suspendidas por criterio crítico`}
                    >
                      <OctagonX size={12} aria-hidden />
                      {r.critical_pct}%
                    </span>
                  ) : (
                    <span className="font-mono tabular-nums text-text-muted">0%</span>
                  )}
                </td>
                <td className="py-1.5">
                  {r.sentiment != null ? (
                    <span className="inline-flex items-center gap-1.5 font-mono tabular-nums text-text-secondary">
                      <span
                        className="h-2 w-2 rounded-full"
                        style={{ background: scoreVar(r.sentiment) }}
                      />
                      {r.sentiment}
                    </span>
                  ) : (
                    <span className="text-text-muted">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * Top problemas recurrentes / "qué cambiar"
 * --------------------------------------------------------------------------- */
export function TopProblems({
  items,
  title = 'Top problemas recurrentes',
}: {
  items: (RecommendationStat | AgentRecommendationStat)[];
  title?: string;
}) {
  if (items.length === 0) {
    return (
      <Card>
        <CardTitle className="mb-2">{title}</CardTitle>
        <p className="text-small text-text-muted">
          Sin recomendaciones registradas en este periodo.
        </p>
      </Card>
    );
  }
  const max = Math.max(...items.map((i) => i.count));
  return (
    <Card>
      <CardTitle className="mb-4 flex items-center gap-2">
        <Repeat size={18} className="text-accent-primary" />
        {title}
      </CardTitle>
      <ul className="flex flex-col gap-3">
        {items.map((it, i) => (
          <li key={i} className="rounded-card bg-bg-secondary p-3">
            <div className="mb-1.5 flex flex-wrap items-center gap-2">
              <PriorityBadge
                priority={(it.priority as 'high' | 'medium' | 'low') ?? 'medium'}
              />
              <span className="flex-1 text-body font-semibold text-text-primary">
                {it.title}
              </span>
              <span className="rounded-control bg-accent-primary/10 px-2 py-0.5 text-small font-mono font-semibold tabular-nums text-accent-primary dark:bg-rust/15 dark:text-rust">
                ×{it.count}
              </span>
            </div>
            <div className="mb-2 h-1 w-full overflow-hidden rounded-full bg-bg-accent">
              <div
                className="h-full rounded-full bg-accent-primary/40 dark:bg-rust/40"
                style={{ width: `${(it.count / max) * 100}%` }}
              />
            </div>
            {it.sample_description && (
              <p className="text-small text-text-secondary">{it.sample_description}</p>
            )}
            {'evidence' in it && it.evidence && (
              <p className="mt-1.5 border-l border-accent-secondary/60 pl-2.5 text-small italic text-text-muted">
                «{it.evidence}»
              </p>
            )}
            <p className="mt-1.5 text-[11px] uppercase tracking-wide text-text-muted">
              {dimensionLabel(it.dimension)}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * Dinámica de conversación — agregado del equipo
 * --------------------------------------------------------------------------- */
export function ConversationStats({ summary }: { summary: ConversationSummary }) {
  const items = [
    { icon: <Mic size={16} />, label: 'Habla del agente', value: summary.avg_agent_talk_pct != null ? `${summary.avg_agent_talk_pct}%` : '—' },
    { icon: <Volume2 size={16} />, label: 'Silencio medio', value: summary.avg_silence_pct != null ? `${summary.avg_silence_pct}%` : '—' },
    { icon: <Gauge size={16} />, label: 'Ratio hablar/escuchar', value: summary.avg_talk_to_listen_ratio?.toFixed(2) ?? '—' },
    { icon: <MessageSquare size={16} />, label: 'Palabras/min (agente)', value: summary.avg_agent_words_per_minute?.toFixed(0) ?? '—' },
    { icon: <Clock size={16} />, label: 'Monólogo más largo', value: formatDuration(summary.avg_longest_monologue_seconds) },
  ];
  return (
    <Card>
      <CardTitle className="mb-4 flex items-center gap-2">
        <MessageSquare size={18} className="text-accent-primary" />
        Dinámica de <span className="hl">conversación</span>
        <span className="text-small font-normal text-text-muted">
          · {summary.calls_measured} llamadas medidas
        </span>
      </CardTitle>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-card bg-border sm:grid-cols-3 lg:grid-cols-5">
        {items.map((it) => (
          <div key={it.label} className="flex flex-col gap-1.5 bg-bg-card p-4">
            <span className="flex items-center gap-1.5 text-text-muted">{it.icon}</span>
            <span className="text-h2 font-mono font-semibold tabular-nums text-text-primary">{it.value}</span>
            <span className="text-small text-text-secondary">{it.label}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * Métricas de conversación de UNA llamada (detalle)
 * --------------------------------------------------------------------------- */
export function ConversationMetricsCard({ metrics }: { metrics: ConversationMetrics }) {
  const agentPct = metrics.agent_talk_pct ?? 0;
  const customerPct = metrics.customer_talk_pct ?? 0;
  const tiles = [
    { label: 'Ratio hablar/escuchar', value: metrics.talk_to_listen_ratio?.toFixed(2) ?? '—' },
    { label: 'Silencio / dead-air', value: metrics.silence_pct != null ? `${metrics.silence_pct}%` : '—' },
    { label: 'Monólogo más largo', value: formatDuration(metrics.longest_agent_monologue_seconds) },
    { label: 'Palabras/min (agente)', value: metrics.agent_words_per_minute?.toFixed(0) ?? '—' },
    { label: 'Turnos/min', value: metrics.turns_per_minute?.toFixed(1) ?? '—' },
  ];
  return (
    <Card>
      <CardTitle className="mb-4 flex items-center gap-2">
        <MessageSquare size={18} className="text-accent-primary" />
        Dinámica de la <span className="hl">conversación</span>
      </CardTitle>
      <div className="mb-1 flex justify-between text-small">
        <span className="font-medium text-accent-primary">Ejecutivo {agentPct}%</span>
        <span className="font-medium text-info">Cliente {customerPct}%</span>
      </div>
      <div className="mb-5 flex h-3 w-full overflow-hidden rounded-full bg-bg-accent">
        <div
          className="h-full bg-accent-primary"
          style={{
            width: `${agentPct}%`,
            transition: 'width var(--duration-reveal) var(--ease-out)',
          }}
        />
        <div
          className="h-full bg-info"
          style={{
            width: `${customerPct}%`,
            transition: 'width var(--duration-reveal) var(--ease-out)',
          }}
        />
      </div>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-card bg-border sm:grid-cols-3 lg:grid-cols-5">
        {tiles.map((t) => (
          <div key={t.label} className="flex flex-col gap-1 bg-bg-card p-3">
            <span className="text-h3 font-mono font-semibold tabular-nums text-text-primary">{t.value}</span>
            <span className="text-[11px] text-text-secondary">{t.label}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * Distribución de scores — donut con leyenda
 * --------------------------------------------------------------------------- */
const DIST_META: Record<string, { label: string; color: string }> = {
  '0-59': { label: 'Banda roja', color: 'var(--danger)' },
  '60-79': { label: 'Aceptable', color: 'var(--warning)' },
  '80-100': { label: 'Excelente', color: 'var(--success)' },
};
export function ScoreDistribution({
  data,
  total,
}: {
  data: { range: string; count: number }[];
  total: number;
}) {
  const segments = data.map((d) => ({
    label: DIST_META[d.range]?.label ?? d.range,
    value: d.count,
    color: DIST_META[d.range]?.color ?? 'var(--info)',
  }));
  return (
    <Card>
      <CardTitle className="mb-4">Distribución de <span className="hl">scores</span></CardTitle>
      <div className="flex flex-wrap items-center justify-center gap-6">
        <Donut segments={segments} centerValue={total} centerLabel="llamadas" />
        <ul className="flex flex-col gap-2.5">
          {data.map((d) => {
            const meta = DIST_META[d.range] ?? { label: d.range, color: 'var(--info)' };
            const pct = total ? Math.round((d.count / total) * 100) : 0;
            return (
              <li key={d.range} className="flex items-center gap-3">
                <span className="h-3 w-3 rounded-sm" style={{ background: meta.color }} />
                <div className="min-w-[120px]">
                  <p className="text-small font-medium text-text-primary">{meta.label}</p>
                  <p className="text-[11px] text-text-muted">{d.range} puntos</p>
                </div>
                <span className="ml-auto text-body font-mono font-semibold tabular-nums text-text-primary">
                  {d.count}
                </span>
                <span className="w-10 text-right text-small font-mono tabular-nums text-text-muted">
                  {pct}%
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * Percentil anónimo del asesor — número grande + barra de posición
 * --------------------------------------------------------------------------- */
export function PercentileCard({ data }: { data: AgentPercentile }) {
  if (!data.available) {
    return (
      <Card className="flex items-center gap-3">
        <Award size={22} className="shrink-0 text-text-muted" />
        <div>
          <p className="text-body font-semibold text-text-primary">Posición no disponible</p>
          <p className="text-small text-text-secondary">
            Aún no hay suficientes asesores con datos en tu campaña para mostrar tu
            posición de forma anónima.
          </p>
        </div>
      </Card>
    );
  }
  const p = data.percentile ?? 0;
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Award size={26} className="text-accent-primary dark:text-rust" />
          <div>
            <p className="flex items-baseline gap-2">
              <span className="text-display font-mono font-semibold tabular-nums text-accent-primary dark:text-rust">
                P{p}
              </span>
              <span className="text-small text-text-secondary">percentil</span>
            </p>
            <p className="text-small text-text-secondary">
              Tu posición anónima en <strong className="text-text-primary">{data.campaign ?? 'tu campaña'}</strong>
              {' · '}puesto {data.rank} de {data.peers_count}
            </p>
          </div>
        </div>
        <div className="flex gap-6 text-center">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-text-muted">Tu media</p>
            <p className="text-h2 font-mono font-semibold tabular-nums" style={{ color: scoreVar(data.agent_avg ?? 0) }}>
              {data.agent_avg?.toFixed(1)}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-text-muted">Media campaña</p>
            <p className="text-h2 font-mono font-semibold tabular-nums text-text-muted">
              {data.campaign_avg?.toFixed(1)}
            </p>
          </div>
        </div>
      </div>
      {/* Barra de posición: marcador en el percentil */}
      <div className="relative mt-5 h-2.5 w-full rounded-full" style={{ background: 'linear-gradient(90deg, var(--danger), var(--warning), var(--success))' }}>
        <div
          className="absolute top-1/2 h-5 w-5 -translate-y-1/2 -translate-x-1/2 rounded-full border-[3px] border-bg-card bg-text-primary shadow"
          style={{ left: `${p}%` }}
          title={`Percentil ${p}`}
        />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-text-muted">
        <span>Por debajo</span>
        <span>Top de la campaña</span>
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * Desglose del asesor por campaña + compliance de nota de producto
 * --------------------------------------------------------------------------- */
export function AgentCampaignBreakdownList({ items }: { items: AgentCampaignBreakdown[] }) {
  if (items.length === 0) return null;
  return (
    <Card>
      <CardTitle className="mb-4">Mi desempeño por <span className="hl">campaña</span></CardTitle>
      <div className="flex flex-col gap-3">
        {items.map((c) => (
          <div key={c.campaign} className="rounded-card bg-bg-secondary p-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-body font-semibold text-text-primary">{c.campaign}</span>
              <span className="flex items-center gap-2">
                <span className="text-small text-text-muted">{c.total_calls} llamadas</span>
                <ScoreBadge score={Math.round(c.avg_score)} />
              </span>
            </div>
            {c.compliance && (
              <div className="mt-3 flex flex-col gap-2 text-small">
                {c.compliance.coverage_pct != null && (
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={15} className="shrink-0 text-success" />
                    <span className="w-44 shrink-0 text-text-secondary">Frases obligatorias</span>
                    <div className="min-w-[60px] flex-1">
                      <MiniProgress value={c.compliance.coverage_pct} color="var(--success)" />
                    </div>
                    <span className="w-10 text-right font-mono font-semibold tabular-nums text-text-primary">
                      {c.compliance.coverage_pct}%
                    </span>
                  </div>
                )}
                {c.compliance.prohibited_hits > 0 && (
                  <span className="flex items-center gap-2 font-medium text-danger">
                    <ShieldAlert size={15} />
                    {c.compliance.prohibited_hits} posible(s) afirmación(es) prohibida(s)
                  </span>
                )}
                {c.compliance.mandatory_missing.length > 0 && (
                  <span className="text-text-muted">
                    Pendiente de mencionar: {c.compliance.mandatory_missing.join(' · ')}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

/* --------------------------------------------------------------------------- *
 * Radar de dimensiones del equipo
 * --------------------------------------------------------------------------- */
export function TeamRadar({ averages }: { averages: Record<string, number> }) {
  if (!averages || Object.keys(averages).length === 0) return null;
  return (
    <Card>
      <CardTitle className="mb-2">Dimensiones del <span className="hl">equipo</span></CardTitle>
      <ScoreRadar scores={averages} seriesLabel="Equipo" />
    </Card>
  );
}
