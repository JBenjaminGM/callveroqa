'use client';

import { useState } from 'react';
import Link from 'next/link';
import { AlertCircle, Clock, Download, Phone, X } from 'lucide-react';
import {
  useAgents,
  useCampaigns,
  useDashboardAlerts,
  useDashboardByCampaign,
  useDashboardSummary,
  useSettings,
  useTopics,
  useTopRecommendations,
} from '@/lib/queries';
import { api, getErrorMessage } from '@/lib/api';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { SectionHeader } from '@/components/ui/section';
import { StatCard } from '@/components/dashboard/stat-card';
import { ScoreGauge, DeltaPill } from '@/components/dashboard/viz';
import { CallsTrendChart } from '@/components/dashboard/trend-chart';
import {
  AlertsPanel,
  CampaignKpiTable,
  ConversationStats,
  ScoreDistribution,
  TeamRadar,
  TopProblems,
  TopicsPanel,
} from '@/components/dashboard/insights';
import { WhoToListen } from '@/components/coaching/who-to-listen';
import { ScoreBadge } from '@/components/ui/badge';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/feedback';
import { cn, formatDuration } from '@/lib/utils';
import type { AgentScore } from '@/types';

const PERIODS = [
  { value: '7d', label: '7 días' },
  { value: '30d', label: '30 días' },
  { value: '90d', label: '90 días' },
];

/** Dashboard del jefe: analítica de alto impacto del equipo. */
export default function DashboardPage() {
  const [period, setPeriod] = useState('30d');
  const [campaign, setCampaign] = useState('');
  const [agentId, setAgentId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [exporting, setExporting] = useState(false);

  const { data: agents } = useAgents();
  const { data: campaigns } = useCampaigns();
  const { data: settings } = useSettings();
  const target = settings?.qa_target_score ?? 90;

  const { data, isLoading, error } = useDashboardSummary({
    period,
    campaign: campaign || undefined,
    agent_id: agentId ? Number(agentId) : undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  const dateFilters = { period, date_from: dateFrom || undefined, date_to: dateTo || undefined };
  const { data: alerts } = useDashboardAlerts(dateFilters);
  const { data: byCampaign } = useDashboardByCampaign(dateFilters);
  const { data: topProblems } = useTopRecommendations({
    ...dateFilters,
    campaign: campaign || undefined,
  });
  const { data: topics } = useTopics({
    ...dateFilters,
    campaign: campaign || undefined,
  });

  /** Descarga el reporte del equipo en CSV con los filtros que están aplicados. */
  async function exportCsv() {
    setExporting(true);
    try {
      const res = await api.get('/dashboard/report.csv', {
        responseType: 'blob',
        params: {
          period,
          campaign: campaign || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        },
      });
      const url = URL.createObjectURL(res.data as Blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `reporte-equipo-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  const datesActive = Boolean(dateFrom || dateTo);
  const hasFilters = Boolean(campaign || agentId || dateFrom || dateTo);
  function clearFilters() {
    setCampaign('');
    setAgentId('');
    setDateFrom('');
    setDateTo('');
    setPeriod('30d');
  }

  const countSeries = data?.calls_by_day.map((d) => d.count) ?? [];
  const trendNum = data ? Number(data.score_trend) : 0;

  return (
    <>
      <Header title="Dashboard" />
      <main className="flex-1 overflow-y-auto bg-bg-primary p-6">
        {/* ---------- Toolbar de filtros ---------- */}
        <Card className="mb-6 flex flex-wrap items-center gap-3 p-3.5">
          {/* Control segmentado de periodo */}
          <div className="flex rounded-control bg-bg-accent p-0.5" role="tablist">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                disabled={datesActive}
                className={cn(
                  'rounded-control px-3.5 py-1.5 text-small font-semibold transition-colors disabled:opacity-40',
                  period === p.value && !datesActive
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'text-text-secondary hover:text-text-primary',
                )}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="mx-1 hidden h-6 w-px bg-border sm:block" />

          <Select
            value={campaign}
            onChange={(e) => setCampaign(e.target.value)}
            aria-label="Campaña"
            className="w-auto min-w-[140px]"
          >
            <option value="">Todas las campañas</option>
            {campaigns?.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </Select>
          <Select
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            aria-label="Ejecutivo"
            className="w-auto min-w-[140px]"
          >
            <option value="">Todos los ejecutivos</option>
            {agents?.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </Select>
          <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} aria-label="Desde" className="w-auto" />
          <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} aria-label="Hasta" className="w-auto" />
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              <X size={16} /> Limpiar
            </Button>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={exportCsv}
            disabled={exporting}
            className="ml-auto"
          >
            <Download size={16} />
            {exporting ? 'Preparando…' : 'Exportar CSV'}
          </Button>
        </Card>

        {isLoading && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-40" />
            ))}
          </div>
        )}

        {error && <ErrorState message={getErrorMessage(error)} />}

        {data && data.total_calls === 0 && (
          <EmptyState
            icon={<Phone size={48} />}
            title={hasFilters ? 'Sin resultados' : 'Aún no hay llamadas analizadas'}
            description={
              hasFilters
                ? 'No hay llamadas que coincidan con los filtros seleccionados.'
                : 'Sube tu primera llamada para empezar a ver métricas del equipo.'
            }
            action={
              hasFilters ? undefined : (
                <Link href="/calls/new" className="rounded-control bg-rust px-4 py-2 text-body text-white">
                  Subir llamada
                </Link>
              )
            }
          />
        )}

        {data && data.total_calls > 0 && (
          <div className="animate-fade-in flex flex-col gap-8">
            {/* ---------- Lo primero: qué hacer hoy ---------- */}
            <section className="flex flex-col gap-3">
              <SectionHeader
                eyebrow="por dónde empezar"
                title={<>A quién <span className="hl">escuchar</span> hoy</>}
              />
              <WhoToListen filters={dateFilters} />
            </section>

            {/* ---------- Resumen ---------- */}
            <section className="flex flex-col gap-3">
              <SectionHeader eyebrow="visión general" title={<>Calidad con <span className="hl">impacto</span></>} />
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                {/* Gauge héroe */}
                <Card className="flex flex-col items-center justify-center gap-3 text-center">
                  <span className="destacado text-[11px] text-text-muted">score qa del equipo</span>
                  <ScoreGauge value={data.average_score} label="sobre 100" />
                  <div className="flex items-center gap-2">
                    <DeltaPill delta={Number.isFinite(trendNum) ? trendNum : null} />
                    <span className="text-small text-text-muted">vs. periodo anterior</span>
                  </div>
                </Card>

                <StatCard
                  label="Llamadas analizadas"
                  value={data.total_calls.toLocaleString('es-PE')}
                  icon={<Phone size={16} />}
                  sparkData={countSeries}
                  caption="en el periodo"
                />
                <StatCard
                  label="En banda roja"
                  value={data.red_call_count}
                  unit={`· ${data.red_call_pct}%`}
                  icon={<AlertCircle size={16} />}
                  accent={data.red_call_count > 0 ? 'var(--danger)' : 'var(--success)'}
                  caption={`umbral < ${settings?.qa_red_call_threshold ?? 60}`}
                />
                <StatCard
                  label="Duración media"
                  value={formatDuration(data.avg_duration_seconds)}
                  icon={<Clock size={16} />}
                  caption="por llamada"
                />
              </div>
            </section>

            {/* ---------- Tendencias ---------- */}
            <section className="flex flex-col gap-3">
              <SectionHeader eyebrow="tendencias" title={<>Evolución y <span className="hl">distribución</span></>} />
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
                <div className="lg:col-span-3">
                  <CallsTrendChart data={data.calls_by_day} target={target} />
                </div>
                <div className="lg:col-span-2">
                  <ScoreDistribution data={data.score_distribution} total={data.total_calls} />
                </div>
              </div>
            </section>

            {/* ---------- Campañas y equipo ---------- */}
            <section className="flex flex-col gap-3">
              <SectionHeader eyebrow="desempeño" title={<>Campañas y <span className="hl">equipo</span></>} />
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {byCampaign && <CampaignKpiTable rows={byCampaign} />}
                <TeamRadar averages={data.team_dimension_averages} />
              </div>
              {topics && <TopicsPanel topics={topics} />}
            </section>

            {/* ---------- Señales ---------- */}
            <section className="flex flex-col gap-3">
              <SectionHeader eyebrow="señales" title={<>Alertas y <span className="hl">oportunidades</span></>} />
              <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
                {alerts && <AlertsPanel alerts={alerts} />}
                {topProblems && <TopProblems items={topProblems} />}
              </div>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Card>
                  <CardTitle className="mb-3">Mejor <span className="hl">desempeño</span></CardTitle>
                  <RankingList items={data.top_performers} />
                </Card>
                <Card>
                  <CardTitle className="mb-3">Oportunidad de <span className="hl">mejora</span></CardTitle>
                  <RankingList items={data.improvement_opportunities} />
                </Card>
              </div>
            </section>

            {/* ---------- Conversación ---------- */}
            {data.conversation_summary && (
              <section className="flex flex-col gap-3">
                <SectionHeader eyebrow="cómo se habla" title={<>Dinámica de <span className="hl">conversación</span></>} />
                <ConversationStats summary={data.conversation_summary} />
              </section>
            )}
          </div>
        )}
      </main>
    </>
  );
}

function RankingList({ items }: { items: AgentScore[] }) {
  if (items.length === 0) {
    return <p className="text-small text-text-muted">Sin datos suficientes.</p>;
  }
  return (
    <ul className="flex flex-col gap-1">
      {items.map((item, i) => {
        const content = (
          <div className="flex items-center gap-3 rounded-card px-2 py-2 transition-colors hover:bg-bg-accent/50">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-bg-accent text-small font-mono font-semibold tabular-nums text-text-secondary">
              {i + 1}
            </span>
            <span className="flex-1 truncate text-body text-text-primary">{item.name}</span>
            {!item.registered && (
              <span className="rounded-control bg-warning/15 px-1.5 py-0.5 text-[11px] font-medium text-warning">
                sin registrar
              </span>
            )}
            <span className="text-small font-mono tabular-nums text-text-muted">{item.total_calls} ll.</span>
            <ScoreBadge score={Math.round(item.avg_score)} />
          </div>
        );
        return (
          <li key={`${item.agent_id ?? 'd'}-${item.name}-${i}`}>
            {item.registered && item.agent_id ? (
              <Link href={`/agents/${item.agent_id}`}>{content}</Link>
            ) : (
              content
            )}
          </li>
        );
      })}
    </ul>
  );
}
