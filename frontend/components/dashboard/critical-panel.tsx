'use client';

import Link from 'next/link';
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { OctagonX } from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/card';
import { DeltaPill } from '@/components/dashboard/viz';
import type { CriticalReport } from '@/types';

function semana(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('es-PE', {
    day: '2-digit',
    month: 'short',
  });
}

/** Cambio entre mitades del periodo, o null si no hay llamadas para medirlo. */
function subida(antes?: number | null, despues?: number | null) {
  return antes == null || despues == null ? null : +(despues - antes).toFixed(1);
}

/**
 * Suspendidas por criterio crítico: la tasa semana a semana y quién suspende.
 *
 * Las alertas avisan de cada llamada suspendida; esta tarjeta enseña el patrón:
 * si es cosa de una persona o del equipo, qué criterio se incumple y si va a
 * más. En banca, eso es lo primero que pregunta una auditoría.
 */
export function CriticalPanel({ report }: { report: CriticalReport }) {
  if (report.total_calls === 0) return null;

  const cambio = subida(report.first_half_pct, report.second_half_pct);
  const conSuspendidas = report.by_agent.filter((a) => a.critical_calls > 0);
  const datos = report.weekly
    .filter((w) => w.total_calls > 0)
    .map((w) => ({ ...w, label: semana(w.week_start) }));

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle className="mb-1 flex items-center gap-2">
            <OctagonX size={18} className="text-danger" />
            Llamadas <span className="hl">suspendidas</span>
          </CardTitle>
          <p className="text-small text-text-secondary">
            Por incumplir un criterio crítico de la rúbrica, semana a semana y
            por asesor.
          </p>
        </div>
        <div className="text-right">
          <p className="font-mono text-h3 font-semibold tabular-nums text-text-primary">
            {report.critical_pct.toFixed(1)} %
          </p>
          <p className="text-[11px] text-text-muted">
            {report.critical_calls} de {report.total_calls} llamadas
          </p>
          {cambio != null && (
            <div className="mt-1 flex items-center justify-end gap-1.5">
              <DeltaPill
                delta={cambio}
                suffix=" pp"
                size="xs"
                higherIsBetter={false}
              />
              <span className="text-[11px] text-text-muted">
                {cambio > 0 ? 'suben' : cambio < 0 ? 'bajan' : 'igual'} en la
                2.ª mitad
              </span>
            </div>
          )}
        </div>
      </div>

      {report.critical_calls === 0 ? (
        <p className="text-small text-text-secondary">
          Ninguna llamada suspendida en el periodo.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div className="h-44 min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={datos} margin={{ top: 4, right: 4, bottom: 0, left: -24 }}>
                <XAxis
                  dataKey="label"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                  interval="preserveStartEnd"
                />
                {/* Hasta el máximo de las semanas y no hasta 100: con tasas del
                    10-30 %, un eje fijo dejaba las barras casi planas. */}
                <YAxis
                  unit="%"
                  domain={[
                    0,
                    (max: number) =>
                      Math.min(100, Math.max(20, Math.ceil(max / 10) * 10)),
                  ]}
                  allowDecimals={false}
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                />
                <Tooltip
                  cursor={{ fill: 'var(--bg-accent)' }}
                  contentStyle={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 8,
                    color: 'var(--text-primary)',
                  }}
                  formatter={(_v, _n, item) => {
                    const w = item.payload as (typeof datos)[number];
                    return [
                      `${w.critical_pct} % (${w.critical_calls} de ${w.total_calls})`,
                      'Suspendidas',
                    ];
                  }}
                  labelFormatter={(l) => `Semana del ${l}`}
                />
                <Bar dataKey="critical_pct" fill="var(--danger)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="flex flex-col gap-3">
            <table className="w-full text-small">
              <thead>
                <tr className="border-b border-border text-left text-text-secondary">
                  <th className="pb-1 pr-3 font-semibold">Asesor</th>
                  <th className="pb-1 pr-3 font-semibold">Susp.</th>
                  <th className="pb-1 pr-3 font-semibold">%</th>
                  <th className="pb-1 font-semibold">Tendencia</th>
                </tr>
              </thead>
              <tbody>
                {conSuspendidas.map((a) => {
                  const c = subida(a.first_half_pct, a.second_half_pct);
                  return (
                    <tr key={a.agent_id} className="align-top">
                      <td className="py-1.5 pr-3">
                        <Link
                          href={`/agents/${a.agent_id}`}
                          className="font-medium text-text-primary hover:text-accent-primary"
                        >
                          {a.agent_name}
                        </Link>
                        {a.top_criterion && (
                          <p className="text-[11px] text-text-muted">
                            {a.top_criterion}
                          </p>
                        )}
                      </td>
                      <td className="py-1.5 pr-3 font-mono tabular-nums text-text-secondary">
                        {a.critical_calls}/{a.total_calls}
                      </td>
                      <td className="py-1.5 pr-3 font-mono font-semibold tabular-nums text-danger">
                        {a.critical_pct.toFixed(0)}
                      </td>
                      <td className="py-1.5">
                        {c == null ? (
                          <span
                            className="text-[11px] text-text-muted"
                            title="Pocas llamadas en una de las mitades del periodo para compararlas"
                          >
                            —
                          </span>
                        ) : (
                          <DeltaPill
                            delta={c}
                            suffix=" pp"
                            size="xs"
                            higherIsBetter={false}
                          />
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {report.top_criteria.length > 0 && (
              <p className="text-[12px] text-text-muted">
                Más incumplido:{' '}
                {report.top_criteria
                  .slice(0, 3)
                  .map((c) => `${c.criterion} (${c.count})`)
                  .join(' · ')}
              </p>
            )}
            <Link
              href="/calls?critical=true"
              className="w-fit text-small text-accent-primary hover:underline"
            >
              Ver las llamadas suspendidas
            </Link>
          </div>
        </div>
      )}
    </Card>
  );
}
