'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Phone, TrendingUp } from 'lucide-react';
import {
  useAgent,
  useAgentDashboard,
  useAgentPercentile,
  useAgentRecommendations,
} from '@/lib/queries';
import { useAuthStore } from '@/lib/auth';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { EmptyState, Skeleton } from '@/components/ui/feedback';
import { ScoreRadar } from '@/components/charts/score-radar';
import {
  AgentCampaignBreakdownList,
  PercentileCard,
  TopProblems,
} from '@/components/dashboard/insights';
import { ScoreGauge, DeltaPill } from '@/components/dashboard/viz';
import { StatCard } from '@/components/dashboard/stat-card';
import { MyPendingEvaluations } from '@/components/coaching/my-pending';
import { CoachingSessions } from '@/components/coaching/coaching-sessions';
import { dimensionLabel, scoreLabel } from '@/lib/utils';

/** Panel personal del asesor: su rendimiento, comparativa y puntos de mejora. */
export default function MyPanelPage() {
  const user = useAuthStore((s) => s.user);
  const agentId = user?.agent_id ?? NaN;
  const [period, setPeriod] = useState('30d');

  const { data: agent } = useAgent(agentId);
  const { data: dash, isLoading } = useAgentDashboard(agentId, period);
  const { data: percentile } = useAgentPercentile(agentId, period);
  const { data: recommendations } = useAgentRecommendations(agentId, period);

  if (!user?.agent_id) {
    return (
      <>
        <Header title="Mi rendimiento" />
        <main className="flex-1 overflow-y-auto p-6">
          <EmptyState
            title="Cuenta sin ejecutivo vinculado"
            description="Tu usuario aún no está asociado a una ficha de ejecutivo. Contacta con tu jefe de área para activarlo."
          />
        </main>
      </>
    );
  }

  return (
    <>
      <Header title="Mi rendimiento" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-h3 text-text-primary">
              Hola, {agent?.name ?? user.name}
            </p>
            <p className="text-small text-text-secondary">
              {agent?.campaign ?? 'Tu desempeño en las llamadas evaluadas'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-40">
              <Select value={period} onChange={(e) => setPeriod(e.target.value)}>
                <option value="7d">Últimos 7 días</option>
                <option value="30d">Últimos 30 días</option>
                <option value="90d">Últimos 90 días</option>
              </Select>
            </div>
            <Link href="/calls">
              <Button variant="secondary" size="sm">
                <Phone size={16} />
                Mis llamadas
              </Button>
            </Link>
          </div>
        </div>

        {/* Lo primero: lo que tiene sin leer. Su media puede esperar. */}
        <div className="mb-6">
          <MyPendingEvaluations enabled={Boolean(user.agent_id)} />
        </div>

        {isLoading && <Skeleton className="h-28" />}

        {dash && (
          <div className="flex flex-col gap-6">
            {/* KPIs personales */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Card className="flex flex-col items-center justify-center gap-2 text-center">
                <span className="destacado text-[11px] text-text-muted">
                  mi score promedio
                </span>
                <ScoreGauge
                  value={dash.average_score}
                  label={scoreLabel(dash.average_score)}
                />
                <div className="flex items-center gap-2">
                  <DeltaPill delta={Number(dash.score_trend)} />
                  <span className="text-small text-text-muted">vs. periodo anterior</span>
                </div>
              </Card>
              <StatCard
                label="Llamadas evaluadas"
                value={dash.total_calls}
                icon={<Phone size={16} />}
                caption="en el periodo"
              />
              <StatCard
                label="Tendencia"
                value={dash.score_trend}
                icon={<TrendingUp size={16} />}
                caption="Evolución de tu score"
              />
            </div>

            {/* Posición anónima dentro de la campaña */}
            {percentile && <PercentileCard data={percentile} />}

            {dash.total_calls > 0 ? (
              <>
                {/* Comparativa por dimensión vs equipo */}
                <Card>
                  <CardTitle className="mb-2">
                    Mi desempeño por dimensión vs. el equipo
                  </CardTitle>
                  <ScoreRadar
                    scores={dash.dimension_averages}
                    teamScores={dash.team_dimension_averages}
                  />
                </Card>

                {/* Fortalezas y puntos de mejora */}
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <Card>
                    <CardTitle className="mb-3">Mis fortalezas</CardTitle>
                    <ul className="flex flex-col gap-2">
                      {dash.strengths.map((d) => (
                        <li
                          key={d}
                          className="flex items-center gap-2 text-body text-text-primary"
                        >
                          <span className="h-2 w-2 rounded-full bg-success" />
                          {dimensionLabel(d)}
                        </li>
                      ))}
                    </ul>
                  </Card>
                  <Card>
                    <CardTitle className="mb-3">Mis puntos de mejora</CardTitle>
                    <ul className="flex flex-col gap-2">
                      {dash.improvement_areas.map((d) => (
                        <li
                          key={d}
                          className="flex items-center gap-2 text-body text-text-primary"
                        >
                          <span className="h-2 w-2 rounded-full bg-danger" />
                          {dimensionLabel(d)}
                        </li>
                      ))}
                    </ul>
                  </Card>
                </div>

                {/* Evolución temporal */}
                {dash.timeline.length > 0 && (
                  <Card>
                    <CardTitle className="mb-4">Mi evolución</CardTitle>
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={dash.timeline}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis
                          dataKey="date"
                          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                        />
                        <YAxis
                          domain={[0, 100]}
                          tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                        />
                        <Tooltip
                          contentStyle={{
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border)',
                            borderRadius: 8,
                            color: 'var(--text-primary)',
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="avg_score"
                          stroke="var(--accent-primary)"
                          strokeWidth={2}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>
                )}

                {/* Qué cambiar: recomendaciones con evidencia */}
                {recommendations && recommendations.recommendations.length > 0 && (
                  <TopProblems
                    items={recommendations.recommendations}
                    title="Qué cambiar (con ejemplos de tus llamadas)"
                  />
                )}

                {/* Desglose por campaña + cumplimiento de la nota de producto */}
                {recommendations && (
                  <AgentCampaignBreakdownList items={recommendations.by_campaign} />
                )}
              </>
            ) : (
              <Card>
                <p className="text-body text-text-secondary">
                  Aún no tienes llamadas evaluadas en este periodo.
                </p>
              </Card>
            )}

            {/* Sus sesiones de coaching y si le sirvieron. */}
            <CoachingSessions
              agentId={user.agent_id}
              agentName={agent?.name ?? user.name}
              canManage={false}
            />
          </div>
        )}
      </main>
    </>
  );
}
