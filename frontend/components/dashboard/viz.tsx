'use client';

/**
 * Primitivas de visualización de datos: nivel "BI premium" pero fiel a la
 * identidad CallVeroQA (plano, geométrico, paleta paper/ink + acentos rust y gold).
 *
 * Todo usa variables CSS de globals.css para tema claro/oscuro automático.
 */

import { ArrowDown, ArrowUp, Minus } from 'lucide-react';
import { scoreLevel } from '@/lib/utils';

/** Color de marca para un score 0-100 (semántico). Devuelve un `var(--…)`. */
export function scoreVar(score: number): string {
  return `var(--${scoreLevel(score)})`;
}

/* --------------------------------------------------------------------------- *
 * ScoreGauge — anillo de progreso con el score en el centro (elemento "héroe")
 * --------------------------------------------------------------------------- */
export function ScoreGauge({
  value,
  size = 168,
  stroke = 13,
  label,
  caption,
  color,
  decimals = 1,
}: {
  value: number;
  size?: number;
  stroke?: number;
  label?: string;
  caption?: string;
  color?: string;
  decimals?: number;
}) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - v / 100);
  const col = color ?? scoreVar(v);
  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
          opacity={0.55}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={col}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          // `gauge-sweep` (globals.css) lo hace barrer desde vacío en el primer
          // pintado; la transición se encarga de los cambios posteriores.
          className="gauge-sweep"
          style={
            {
              transition:
                'stroke-dashoffset var(--duration-reveal) var(--ease-out)',
              '--gauge-circumference': c,
            } as React.CSSProperties
          }
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono font-semibold tabular-nums leading-none"
          style={{ color: col, fontSize: size * 0.3 }}
        >
          {Number.isFinite(v) ? v.toFixed(decimals) : '—'}
        </span>
        {label && (
          <span className="mt-1 text-small font-medium text-text-secondary">
            {label}
          </span>
        )}
        {caption && (
          <span className="text-[11px] text-text-muted">{caption}</span>
        )}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------------- *
 * Sparkline — mini tendencia (área) para incrustar en KPI cards
 * --------------------------------------------------------------------------- */
export function Sparkline({
  data,
  width = 120,
  height = 36,
  color = 'var(--accent-primary)',
  fill = true,
  strokeWidth = 2,
}: {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: boolean;
  strokeWidth?: number;
}) {
  const pts = (data ?? []).filter((n) => Number.isFinite(n));
  if (pts.length < 2) {
    return <svg width={width} height={height} aria-hidden />;
  }
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const pad = strokeWidth;
  const stepX = (width - pad * 2) / (pts.length - 1);
  const coords = pts.map((p, i) => {
    const x = pad + i * stepX;
    const y = pad + (height - pad * 2) * (1 - (p - min) / range);
    return [x, y] as const;
  });
  const line = coords.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  const area = `${line} L${coords[coords.length - 1][0].toFixed(1)},${height} L${coords[0][0].toFixed(1)},${height} Z`;
  const gid = `spark-${Math.round(coords[0][1] * 100)}-${pts.length}`;
  return (
    <svg width={width} height={height} className="overflow-visible">
      {fill && (
        <>
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <path d={area} fill={`url(#${gid})`} />
        </>
      )}
      <path
        d={line}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* --------------------------------------------------------------------------- *
 * Donut — distribución con etiqueta central (p. ej. tramos de score)
 * --------------------------------------------------------------------------- */
export function Donut({
  segments,
  size = 168,
  stroke = 18,
  centerValue,
  centerLabel,
}: {
  segments: { label: string; value: number; color: string }[];
  size?: number;
  stroke?: number;
  centerValue?: string | number;
  centerLabel?: string;
}) {
  const total = segments.reduce((a, s) => a + s.value, 0);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  let acc = 0;
  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
          opacity={0.4}
        />
        {total > 0 &&
          segments.map((s, i) => {
            const frac = s.value / total;
            const dash = frac * c;
            const seg = (
              <circle
                key={i}
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                stroke={s.color}
                strokeWidth={stroke}
                strokeDasharray={`${dash} ${c - dash}`}
                strokeDashoffset={-acc}
                style={{
                  transition:
                    'stroke-dasharray var(--duration-reveal) var(--ease-out)',
                }}
              />
            );
            acc += dash;
            return seg;
          })}
      </svg>
      {(centerValue != null || centerLabel) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {centerValue != null && (
            <span className="text-h2 font-mono font-semibold tabular-nums text-text-primary">
              {centerValue}
            </span>
          )}
          {centerLabel && (
            <span className="text-[11px] text-text-muted">{centerLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------------------------- *
 * MiniProgress — barra horizontal compacta (para tablas/tiles)
 * --------------------------------------------------------------------------- */
export function MiniProgress({
  value,
  color,
  height = 6,
  track = 'var(--bg-accent)',
}: {
  value: number;
  color?: string;
  height?: number;
  track?: string;
}) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div
      className="w-full overflow-hidden rounded-full"
      style={{ height, background: track }}
    >
      <div
        className="h-full rounded-full"
        style={{
          width: `${v}%`,
          background: color ?? scoreVar(v),
          transition: 'width var(--duration-reveal) var(--ease-out)',
        }}
      />
    </div>
  );
}

/* --------------------------------------------------------------------------- *
 * DeltaPill — variación vs periodo anterior, con flecha y color semántico
 * --------------------------------------------------------------------------- */
export function DeltaPill({
  delta,
  suffix = '',
  neutralIsGood = true,
  size = 'sm',
}: {
  delta?: number | null;
  suffix?: string;
  neutralIsGood?: boolean;
  size?: 'sm' | 'xs';
}) {
  if (delta == null || Number.isNaN(delta)) {
    return <span className="text-small text-text-muted">—</span>;
  }
  const up = delta > 0;
  const flat = delta === 0;
  const good = flat ? neutralIsGood : up;
  const cls = good ? 'text-success bg-success/10' : 'text-danger bg-danger/10';
  // Icono dibujado, no un glifo unicode. El resto de la aplicación usa lucide:
  // una flecha de texto hereda la métrica de la fuente y se alinea distinto en
  // cada plataforma, que es justo el detalle que delata el atajo.
  const Icono = flat ? Minus : up ? ArrowUp : ArrowDown;
  const lado = size === 'xs' ? 12 : 14;
  const pad = size === 'xs' ? 'px-1.5 py-0.5 text-[11px]' : 'px-2 py-0.5 text-small';
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-control font-mono font-semibold tabular-nums ${pad} ${cls}`}
    >
      <Icono size={lado} aria-hidden className="shrink-0" />
      {Math.abs(delta).toFixed(1)}
      {suffix}
    </span>
  );
}

/* --------------------------------------------------------------------------- *
 * BrandTooltip — contenido de tooltip de Recharts con estilo de marca
 * --------------------------------------------------------------------------- */
export function BrandTooltip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color?: string }[];
  label?: string;
  formatter?: (v: number, name: string) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-card bg-bg-card px-3 py-2 shadow-lg ring-1 ring-border">
      {label != null && (
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-text-muted">
          {label}
        </p>
      )}
      {payload.map((p, i) => (
        <p key={i} className="flex items-center gap-2 text-small text-text-primary">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: p.color ?? 'var(--accent-primary)' }}
          />
          <span className="text-text-secondary">{p.name}:</span>
          <span className="font-mono font-semibold tabular-nums">
            {formatter ? formatter(p.value, p.name) : p.value}
          </span>
        </p>
      ))}
    </div>
  );
}
