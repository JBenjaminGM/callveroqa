'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { GraduationCap, Plus, Trash2 } from 'lucide-react';
import {
  useCoachingSessions,
  useCoachingSuggestions,
  useCreateCoachingSession,
  useDeleteCoachingSession,
  useRubric,
} from '@/lib/queries';
import { getErrorMessage } from '@/lib/api';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input, Textarea } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Spinner } from '@/components/ui/feedback';
import { cn, formatDate } from '@/lib/utils';
import type {
  CoachingMeasure,
  CoachingSession,
  CoachingVerdict,
} from '@/types';

// Las mismas reglas que el backend (coaching_session_service.py): por debajo de
// tres llamadas a cada lado no hay veredicto.
const MIN_LLAMADAS = 3;

const VEREDICTOS: Record<
  CoachingVerdict,
  { label: string; className: string }
> = {
  improved: { label: 'Funcionó', className: 'bg-success/15 text-success' },
  worsened: { label: 'No funcionó', className: 'bg-danger/15 text-danger' },
  no_change: {
    label: 'Sin efecto medible',
    className: 'bg-warning/15 text-warning',
  },
  pending: { label: 'Faltan llamadas', className: 'bg-info/15 text-info' },
  no_baseline: {
    label: 'Sin línea base',
    className: 'bg-bg-accent text-text-secondary',
  },
};

function hoyISO(): string {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
}

/** Días desde época de una fecha «AAAA-MM-DD», en hora local. */
function dia(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).getTime();
}

function puntos(n: number): string {
  const abs = Math.abs(n).toFixed(1).replace('.0', '');
  return `${abs} ${abs === '1' ? 'punto' : 'puntos'}`;
}

function movimiento(delta: number): string {
  if (delta === 0) return 'se quedó igual';
  return `${delta > 0 ? 'subió' : 'bajó'} ${puntos(delta)}`;
}

/**
 * La frase que explica el veredicto con sus números. Sin ella, «no funcionó»
 * junto a una nota que subió parece un error; con ella se entiende que el
 * equipo subió más.
 */
function explicacion(m: CoachingMeasure, persona: string): string {
  if (m.verdict === 'no_baseline') {
    return `${persona} tenía ${m.before_count} ${m.before_count === 1 ? 'llamada' : 'llamadas'} en los ${m.window_days} días anteriores: no hay con qué comparar.`;
  }
  if (m.verdict === 'pending') {
    if (m.after_count < MIN_LLAMADAS) {
      return `Lleva ${m.after_count} de ${MIN_LLAMADAS} llamadas necesarias después de la sesión.${m.window_closed ? '' : ' Se sigue midiendo.'}`;
    }
    return 'Aún no hay llamadas suficientes del resto del equipo en esas semanas para saber si el cambio es suyo o de todos.';
  }
  const propio = `En esta dimensión ${movimiento(m.delta ?? 0)}`;
  if (m.team_delta == null) {
    return `${propio}. No hay otros asesores con los que comparar, así que se juzga el cambio tal cual.`;
  }
  return `${propio}; el resto del equipo ${movimiento(m.team_delta)} en las mismas semanas. El efecto neto es de ${m.net_delta && m.net_delta > 0 ? '+' : m.net_delta && m.net_delta < 0 ? '−' : ''}${puntos(m.net_delta ?? 0)}.`;
}

/**
 * Coaching de un asesor: cada sesión con el antes y el después de la dimensión
 * que se trabajó.
 *
 * Es lo que convierte «hablé con ella» en un dato: si la nota de esa dimensión
 * se movió después de la sesión, y si se movió más que la del resto del equipo.
 */
export function CoachingSessions({
  agentId,
  agentName,
  canManage,
}: {
  agentId: number;
  agentName: string;
  canManage: boolean;
}) {
  const { data: sesiones, isLoading } = useCoachingSessions(agentId);
  const [abierto, setAbierto] = useState(false);

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle className="mb-1 flex items-center gap-2">
            <GraduationCap size={18} className="text-accent-primary" />
            Coaching
          </CardTitle>
          <p className="max-w-2xl text-small text-text-secondary">
            Cada sesión se trabaja sobre un criterio de la rúbrica y se mide
            sola: la nota de ese criterio en los 30 días anteriores frente a los
            30 posteriores, descontando lo que se movió el resto del equipo.
          </p>
        </div>
        {canManage && !abierto && (
          <Button size="sm" onClick={() => setAbierto(true)}>
            <Plus size={16} />
            Registrar sesión
          </Button>
        )}
      </div>

      {abierto && (
        <NewSessionForm agentId={agentId} onClose={() => setAbierto(false)} />
      )}

      {isLoading && <Spinner />}

      {sesiones && sesiones.length === 0 && !abierto && (
        <p className="text-body text-text-secondary">
          {canManage
            ? `Todavía no hay sesiones de coaching con ${agentName}.`
            : 'Todavía no tienes sesiones de coaching registradas.'}
        </p>
      )}

      <ul className="flex flex-col gap-4">
        {sesiones?.map((s) => (
          <li key={s.id}>
            <SessionItem
              session={s}
              persona={canManage ? agentName : 'Tu nota'}
              canManage={canManage}
            />
          </li>
        ))}
      </ul>
    </Card>
  );
}

function NewSessionForm({
  agentId,
  onClose,
}: {
  agentId: number;
  onClose: () => void;
}) {
  const { data: rubrica } = useRubric();
  const { data: sugerencias } = useCoachingSuggestions(agentId);
  const crear = useCreateCoachingSession();

  // Se propone la dimensión que más se aleja por debajo del equipo, si la hay.
  const propuesta = sugerencias?.find((s) => (s.gap ?? 0) < 0);
  const [elegida, setElegida] = useState<string | null>(null);
  const dimension = elegida ?? propuesta?.dimension_key ?? '';
  const [fecha, setFecha] = useState(hoyISO());
  const [notas, setNotas] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await crear.mutateAsync({
        agent_id: agentId,
        dimension_key: dimension,
        held_on: fecha,
        notes: notas.trim() || undefined,
      });
      onClose();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }

  const alejadas = sugerencias?.filter((s) => (s.gap ?? 0) < 0) ?? [];

  return (
    <form
      onSubmit={enviar}
      className="mb-5 flex flex-col gap-4 rounded-card bg-bg-secondary p-4"
    >
      {alejadas.length > 0 && (
        <div>
          <p className="mb-2 text-small text-text-secondary">
            Dónde más se separa del equipo en los últimos 30 días:
          </p>
          <div className="flex flex-wrap gap-2">
            {alejadas.map((s) => (
              <button
                key={s.dimension_key}
                type="button"
                onClick={() => setElegida(s.dimension_key)}
                className={cn(
                  'rounded-control border px-3 py-1.5 text-small transition-colors duration-ui',
                  dimension === s.dimension_key
                    ? 'border-accent-primary bg-accent-primary/10 text-text-primary'
                    : 'border-border text-text-secondary hover:border-accent-primary',
                )}
              >
                {s.dimension_name}
                <span className="ml-1.5 font-mono tabular-nums text-danger">
                  {s.gap?.toFixed(1)}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto]">
        <div>
          <Label htmlFor="coaching-dim">Criterio trabajado</Label>
          <Select
            id="coaching-dim"
            value={dimension}
            onChange={(e) => setElegida(e.target.value)}
            required
          >
            <option value="" disabled>
              Elige un criterio de la rúbrica
            </option>
            {rubrica?.map((d) => (
              <option key={d.dimension_key} value={d.dimension_key}>
                {d.dimension_name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="coaching-fecha">Fecha de la sesión</Label>
          <Input
            id="coaching-fecha"
            type="date"
            value={fecha}
            max={hoyISO()}
            onChange={(e) => setFecha(e.target.value)}
            required
          />
        </div>
      </div>

      <div>
        <Label htmlFor="coaching-notas">Qué se trabajó y qué se acordó</Label>
        <Textarea
          id="coaching-notas"
          rows={3}
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          placeholder="Escuchamos la llamada del martes y practicamos cómo responder a «me lo pienso»."
        />
      </div>

      {error && <p className="text-small text-danger">{error}</p>}

      <div className="flex gap-2">
        <Button type="submit" disabled={!dimension || crear.isPending}>
          {crear.isPending && <Spinner />}
          Guardar sesión
        </Button>
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}

function SessionItem({
  session: s,
  persona,
  canManage,
}: {
  session: CoachingSession;
  persona: string;
  canManage: boolean;
}) {
  const borrar = useDeleteCoachingSession();
  const m = s.measure;
  const v = VEREDICTOS[m.verdict];

  async function onBorrar() {
    if (!confirm('¿Borrar esta sesión de coaching? No afecta a las llamadas.')) {
      return;
    }
    await borrar.mutateAsync(s.id);
  }

  return (
    <div className="rounded-card bg-bg-secondary p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-body font-semibold text-text-primary">
            {s.dimension_name}
          </p>
          <p className="text-small text-text-secondary">
            {formatDate(s.held_on)}
            {s.coach_name ? ` · con ${s.coach_name}` : ''}
            {s.call_id ? (
              <>
                {' · a partir de la '}
                <Link
                  href={`/calls/${s.call_id}`}
                  className="text-accent-primary hover:underline"
                >
                  llamada #{s.call_id}
                </Link>
              </>
            ) : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'rounded-control px-2.5 py-1 text-small font-semibold',
              v.className,
            )}
          >
            {v.label}
          </span>
          {canManage && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onBorrar}
              disabled={borrar.isPending}
              aria-label="Borrar sesión"
            >
              <Trash2 size={16} />
            </Button>
          )}
        </div>
      </div>

      {s.notes && (
        <p className="mt-2 whitespace-pre-line text-small text-text-primary">
          {s.notes}
        </p>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,15rem)_1fr]">
        <dl className="grid grid-cols-2 gap-3 self-start">
          <Cifra
            label="Antes"
            valor={m.before_avg}
            pie={`${m.before_count} ${m.before_count === 1 ? 'llamada' : 'llamadas'}`}
          />
          <Cifra
            label="Después"
            valor={m.after_avg}
            pie={`${m.after_count} ${m.after_count === 1 ? 'llamada' : 'llamadas'}`}
          />
          {/* Sin color: lo que hizo el equipo es contexto, no mérito suyo. */}
          <Cifra
            label="Equipo"
            valor={m.team_delta}
            signo
            neutro
            pie="cambio en esas semanas"
          />
          <Cifra label="Efecto neto" valor={m.net_delta} signo destacado />
        </dl>
        {m.points.length > 0 && <BeforeAfterChart session={s} />}
      </div>

      <p className="mt-3 text-small text-text-secondary">
        {explicacion(m, persona)}
      </p>
    </div>
  );
}

function Cifra({
  label,
  valor,
  pie,
  signo = false,
  neutro = false,
  destacado = false,
}: {
  label: string;
  valor?: number | null;
  pie?: string;
  signo?: boolean;
  neutro?: boolean;
  destacado?: boolean;
}) {
  const texto =
    valor == null
      ? '—'
      : `${signo && valor > 0 ? '+' : ''}${valor.toFixed(1)}`;
  const color =
    !signo || neutro || valor == null || valor === 0
      ? 'text-text-primary'
      : valor > 0
        ? 'text-success'
        : 'text-danger';
  return (
    <div>
      <dt className="destacado text-[11px] text-text-muted">{label}</dt>
      <dd
        className={cn(
          'font-mono font-semibold tabular-nums',
          destacado ? 'text-h3' : 'text-body',
          color,
        )}
      >
        {texto}
      </dd>
      {pie && <dd className="text-[11px] text-text-muted">{pie}</dd>}
    </div>
  );
}

/**
 * Las llamadas del asesor en la ventana, antes y después de la sesión, con la
 * media de cada lado. Una media sola esconde si el cambio es de todas las
 * llamadas o de una muy buena; los puntos lo enseñan.
 */
function BeforeAfterChart({ session: s }: { session: CoachingSession }) {
  const m = s.measure;
  const toPoint = (p: CoachingSession['measure']['points'][number]) => ({
    x: dia(p.date),
    y: p.score,
    call: p.call_id,
  });
  const antes = m.points.filter((p) => p.phase === 'before').map(toPoint);
  const despues = m.points.filter((p) => p.phase === 'after').map(toPoint);
  const inicio = dia(m.window_start);
  const sesion = dia(s.held_on);
  const fin = dia(m.window_end);

  return (
    <div className="h-44 min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <XAxis
            type="number"
            dataKey="x"
            domain={[inicio, fin]}
            ticks={[inicio, sesion, fin]}
            tickFormatter={(t: number) =>
              new Date(t).toLocaleDateString('es-PE', {
                day: '2-digit',
                month: 'short',
              })
            }
            tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            domain={[0, 100]}
            ticks={[0, 50, 100]}
            tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          />
          <Tooltip
            cursor={false}
            contentStyle={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              color: 'var(--text-primary)',
            }}
            formatter={(value: number, name: string) =>
              name === 'y' ? [value, 'Nota'] : [value, name]
            }
            labelFormatter={() => ''}
          />
          <ReferenceLine
            x={sesion}
            stroke="var(--accent-primary)"
            strokeDasharray="4 3"
            label={{
              value: 'sesión',
              position: 'insideTopRight',
              fill: 'var(--accent-primary)',
              fontSize: 11,
            }}
          />
          {m.before_avg != null && (
            <ReferenceLine
              segment={[
                { x: inicio, y: m.before_avg },
                { x: sesion, y: m.before_avg },
              ]}
              stroke="var(--text-muted)"
              strokeWidth={2}
            />
          )}
          {m.after_avg != null && (
            <ReferenceLine
              segment={[
                { x: sesion, y: m.after_avg },
                { x: fin, y: m.after_avg },
              ]}
              stroke="var(--accent-primary)"
              strokeWidth={2}
            />
          )}
          <Scatter data={antes} fill="var(--text-muted)" />
          <Scatter data={despues} fill="var(--accent-primary)" />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
