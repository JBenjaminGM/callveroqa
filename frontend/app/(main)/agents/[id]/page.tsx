'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ArrowLeft, KeyRound, Pencil, UserX } from 'lucide-react';
import {
  useAgent,
  useAgentDashboard,
  useCreateAgentLogin,
  useDeactivateAgent,
  useUpdateAgent,
} from '@/lib/queries';
import { useAuthStore } from '@/lib/auth';
import { getErrorMessage } from '@/lib/api';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { ErrorState, Skeleton, Spinner } from '@/components/ui/feedback';
import { ScoreRadar } from '@/components/charts/score-radar';
import { CoachingSessions } from '@/components/coaching/coaching-sessions';
import { dimensionLabel } from '@/lib/utils';
import type { AgentDetail } from '@/types';

/** Perfil de un ejecutivo con su performance y datos editables. */
export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [period, setPeriod] = useState('30d');
  const { data: agent, isLoading, error } = useAgent(id);
  const { data: dash } = useAgentDashboard(id, period);
  const updateAgent = useUpdateAgent();
  const deactivate = useDeactivateAgent();
  const user = useAuthStore((s) => s.user);
  const isManager = user?.role === 'admin' || user?.role === 'jefe';

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [campaign, setCampaign] = useState('');

  function startEdit() {
    setName(agent?.name ?? '');
    setCampaign(agent?.campaign ?? '');
    setEditing(true);
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    await updateAgent.mutateAsync({
      id,
      name: name.trim(),
      campaign: campaign.trim() || undefined,
    });
    setEditing(false);
  }

  async function onDeactivate() {
    if (!confirm('¿Desactivar este ejecutivo? Su historial se conservará.')) {
      return;
    }
    await deactivate.mutateAsync(id);
    router.push('/agents');
  }

  return (
    <>
      <Header title="Perfil del ejecutivo" />
      <main className="flex-1 overflow-y-auto p-6">
        <button
          onClick={() => router.push('/agents')}
          className="mb-4 flex items-center gap-1.5 text-small text-text-secondary
                     transition-colors hover:text-accent-primary"
        >
          <ArrowLeft size={16} />
          Volver al equipo
        </button>

        {isLoading && <Skeleton className="h-28" />}
        {error && <ErrorState message={getErrorMessage(error)} />}

        {agent && (
          <div className="flex flex-col gap-6">
            {/* Cabecera / datos */}
            <Card className="flex flex-wrap items-center justify-between gap-4">
              {editing ? (
                <form
                  onSubmit={saveEdit}
                  className="flex flex-wrap items-end gap-3"
                >
                  <div>
                    <Label htmlFor="name">Nombre</Label>
                    <Input
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="campaign">Campaña</Label>
                    <Input
                      id="campaign"
                      value={campaign}
                      onChange={(e) => setCampaign(e.target.value)}
                    />
                  </div>
                  <Button type="submit" disabled={updateAgent.isPending}>
                    Guardar
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setEditing(false)}
                  >
                    Cancelar
                  </Button>
                </form>
              ) : (
                <>
                  <div className="flex items-center gap-3">
                    <div
                      className="flex h-12 w-12 items-center justify-center rounded-full
                                 bg-accent-secondary text-h3 font-bold text-white"
                    >
                      {agent.name
                        .split(' ')
                        .map((p) => p[0])
                        .slice(0, 2)
                        .join('')
                        .toUpperCase()}
                    </div>
                    <div>
                      <p className="text-h3 text-text-primary">{agent.name}</p>
                      <p className="text-small text-text-secondary">
                        {agent.campaign ?? 'Sin campaña'}
                        {agent.email ? ` · ${agent.email}` : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" onClick={startEdit}>
                      <Pencil size={16} />
                      Editar
                    </Button>
                    {agent.active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={onDeactivate}
                        disabled={deactivate.isPending}
                      >
                        <UserX size={16} />
                        Desactivar
                      </Button>
                    )}
                  </div>
                </>
              )}
            </Card>

            {/* Crear acceso de asesor (solo managers) */}
            {isManager && <AgentLoginCard agent={agent} />}

            {/* Periodo */}
            <div className="flex items-center justify-between">
              <p className="text-body text-text-secondary">
                Performance del ejecutivo
              </p>
              <div className="w-40">
                <Select
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                >
                  <option value="7d">Últimos 7 días</option>
                  <option value="30d">Últimos 30 días</option>
                  <option value="90d">Últimos 90 días</option>
                </Select>
              </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Card className="flex flex-col gap-1">
                <p className="text-small text-text-secondary">
                  Llamadas analizadas
                </p>
                <p className="text-kpi font-mono text-accent-primary">
                  {dash?.total_calls ?? agent.total_calls}
                </p>
              </Card>
              <Card className="flex flex-col gap-1">
                <p className="text-small text-text-secondary">
                  Score promedio
                </p>
                <p className="text-kpi font-mono text-accent-primary">
                  {(dash?.average_score ?? agent.average_score ?? 0).toFixed(
                    1,
                  )}
                </p>
              </Card>
              <Card className="flex flex-col gap-1">
                <p className="text-small text-text-secondary">Tendencia</p>
                <p className="text-kpi font-mono text-accent-primary">
                  {dash?.score_trend ?? '—'}
                </p>
              </Card>
            </div>

            {dash && dash.total_calls > 0 && (
              <>
                {/* Radar vs equipo */}
                <Card>
                  <CardTitle className="mb-2">
                    Comparativa por dimensión vs. equipo
                  </CardTitle>
                  <ScoreRadar
                    scores={dash.dimension_averages}
                    teamScores={dash.team_dimension_averages}
                  />
                </Card>

                {/* Fortalezas y mejoras */}
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <Card>
                    <CardTitle className="mb-3">Top 3 fortalezas</CardTitle>
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
                    <CardTitle className="mb-3">
                      Top 3 áreas de mejora
                    </CardTitle>
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
                    <CardTitle className="mb-4">Evolución temporal</CardTitle>
                    <ResponsiveContainer width="100%" height={260}>
                      <LineChart data={dash.timeline}>
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="var(--border)"
                        />
                        <XAxis
                          dataKey="date"
                          tick={{
                            fill: 'var(--text-secondary)',
                            fontSize: 11,
                          }}
                        />
                        <YAxis
                          domain={[0, 100]}
                          tick={{
                            fill: 'var(--text-secondary)',
                            fontSize: 12,
                          }}
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
              </>
            )}

            {dash && dash.total_calls === 0 && (
              <Card>
                <p className="text-body text-text-secondary">
                  Este ejecutivo aún no tiene llamadas analizadas en el periodo
                  seleccionado.
                </p>
              </Card>
            )}

            {/* Coaching con su antes y después. No depende del periodo elegido
                arriba: cada sesión se mide en su propia ventana. */}
            <CoachingSessions
              agentId={id}
              agentName={agent.name}
              canManage={isManager}
            />
          </div>
        )}
      </main>
    </>
  );
}

/**
 * Tarjeta para crear la cuenta de acceso (rol asesor) de un ejecutivo, de modo
 * que pueda entrar a ver su propio rendimiento en /mi-panel.
 */
function AgentLoginCard({ agent }: { agent: AgentDetail }) {
  const createLogin = useCreateAgentLogin();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState(agent.email ?? '');
  const [password, setPassword] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null);
    setErr(null);
    try {
      await createLogin.mutateAsync({
        id: agent.id,
        email: email.trim(),
        password,
        name: agent.name,
      });
      setMsg(`Acceso creado para ${email.trim()}. Ya puede iniciar sesión.`);
      setPassword('');
      setOpen(false);
    } catch (e2) {
      setErr(getErrorMessage(e2));
    }
  }

  return (
    <Card>
      <CardTitle className="mb-1 flex items-center gap-2">
        <KeyRound size={18} className="text-accent-primary" />
        Acceso del asesor
      </CardTitle>
      <p className="mb-3 text-small text-text-secondary">
        Crea una cuenta para que {agent.name} entre a ver solo su propio
        rendimiento.
      </p>

      {msg && <p className="mb-3 text-small text-success">{msg}</p>}

      {!open ? (
        <Button variant="secondary" size="sm" onClick={() => setOpen(true)}>
          <KeyRound size={16} />
          Crear acceso de asesor
        </Button>
      ) : (
        <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
          <div className="w-60">
            <Label htmlFor="login-email">Email de acceso</Label>
            <Input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="asesor@empresa.com"
              required
            />
          </div>
          <div className="w-52">
            <Label htmlFor="login-pass">Contraseña (mín. 8)</Label>
            <Input
              id="login-pass"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <Button type="submit" disabled={createLogin.isPending}>
            {createLogin.isPending ? <Spinner /> : <KeyRound size={16} />}
            Crear acceso
          </Button>
          <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
        </form>
      )}

      {err && <p className="mt-3 text-small text-danger">{err}</p>}
    </Card>
  );
}
