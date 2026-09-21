'use client';

import Link from 'next/link';
import {
  EarOff,
  Headphones,
  MessageSquareWarning,
  OctagonX,
  TrendingDown,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/feedback';
import { useWhoToListen, type DashboardFilters } from '@/lib/queries';
import { formatDate, scoreColor } from '@/lib/utils';
import type { ListenSuggestion } from '@/types';

/**
 * Con lo que abre el panel: qué llamada poner ahora y por qué.
 *
 * Una media dice cómo va el equipo pero no qué hacer al abrir la pantalla.
 * Esto responde a la pregunta con la que un jefe empieza el día.
 */
export function WhoToListen({ filters }: { filters: DashboardFilters }) {
  const { data, isLoading } = useWhoToListen({ ...filters, limit: 5 });

  if (isLoading) return <Skeleton className="h-48" />;
  // Sin nada urgente no se enseña una tarjeta vacía: se cede el sitio a los KPIs.
  if (!data?.length) return null;

  return (
    <Card>
      <p className="mb-4 text-small text-text-secondary">
        Cinco llamadas como mucho, cada una con el motivo por el que sale. En
        orden de urgencia, no por nota.
      </p>
      <ol className="flex flex-col gap-2">
        {data.map((s, i) => (
          <SuggestionRow key={s.call_id} suggestion={s} index={i + 1} />
        ))}
      </ol>
    </Card>
  );
}

const ICONOS: Record<string, React.ReactNode> = {
  review_requested: <MessageSquareWarning size={16} />,
  critical_failed: <OctagonX size={16} />,
  red_unreviewed: <Headphones size={16} />,
  below_own_average: <TrendingDown size={16} />,
  never_reviewed_agent: <EarOff size={16} />,
};

const COLOR_PRIORIDAD: Record<string, string> = {
  high: 'var(--danger)',
  medium: 'var(--warning)',
  low: 'var(--text-muted)',
};

function SuggestionRow({
  suggestion: s,
  index,
}: {
  suggestion: ListenSuggestion;
  index: number;
}) {
  const color = COLOR_PRIORIDAD[s.priority] ?? 'var(--text-muted)';
  return (
    <li>
      <Link
        href={`/calls/${s.call_id}`}
        className="flex items-start gap-3 rounded-card bg-bg-secondary p-3
                   transition-colors hover:bg-bg-accent"
      >
        <span
          className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center
                     rounded-full text-[11px] font-semibold"
          style={{ background: `${color}22`, color }}
          aria-hidden
        >
          {index}
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2 text-body font-semibold text-text-primary">
            <span style={{ color }}>{ICONOS[s.reason]}</span>
            {s.title}
          </p>
          <p className="mt-0.5 line-clamp-2 text-small text-text-secondary">
            {s.description}
          </p>
          <p className="mt-1 text-small text-text-muted">
            Llamada #{s.call_id}
            {s.agent_name ? ` · ${s.agent_name}` : ''}
            {s.call_date ? ` · ${formatDate(s.call_date)}` : ''}
          </p>
        </div>
        {s.score != null && (
          <span
            className="shrink-0 font-mono text-h3 font-semibold tabular-nums"
            style={{ color: scoreColor(s.score) }}
          >
            {s.score}
          </span>
        )}
      </Link>
    </li>
  );
}
