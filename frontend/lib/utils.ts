import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Combina clases de Tailwind resolviendo conflictos. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Clasificación de un score según la regla de negocio RN-03. */
export type ScoreLevel = 'success' | 'warning' | 'danger';

export function scoreLevel(score: number): ScoreLevel {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warning';
  return 'danger';
}

export function scoreLabel(score: number): string {
  if (score >= 80) return 'Excelente';
  if (score >= 60) return 'Aceptable';
  return 'Requiere atención';
}

/** Color CSS asociado al nivel de un score. */
export function scoreColor(score: number): string {
  const level = scoreLevel(score);
  return `var(--${level})`;
}

/** Formatea una duración en segundos como "m:ss". */
export function formatDuration(seconds?: number | null): string {
  if (seconds == null) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Formatea una fecha ISO como "dd/mm/aaaa". */
export function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  // Una fecha sin hora («2026-08-08») la interpreta `Date` como medianoche UTC,
  // y en América eso cae el día anterior. Se construye en hora local.
  const soloFecha = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  const d = soloFecha
    ? new Date(+soloFecha[1], +soloFecha[2] - 1, +soloFecha[3])
    : new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('es-PE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

/** Formatea una fecha ISO con hora. */
export function formatDateTime(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('es-PE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Nombres legibles de las dimensiones por defecto de la rúbrica. */
export const DIMENSION_LABELS: Record<string, string> = {
  greeting: 'Saludo y protocolo',
  assertiveness: 'Asertividad y tono',
  promotions: 'Promociones / productos',
  compliance: 'Cumplimiento normativo',
  resolution: 'Resolución efectiva',
  objections: 'Manejo de objeciones',
  sentiment: 'Sentimiento del cliente',
};

/**
 * Nombre legible de una dimensión. Las dimensiones por defecto usan el mapa de
 * arriba; las categorías personalizadas (añadidas en la rúbrica) se humanizan a
 * partir de su clave (p.ej. "deteccion_de_fraude" → "Deteccion de fraude").
 */
export function dimensionLabel(key: string): string {
  if (DIMENSION_LABELS[key]) return DIMENSION_LABELS[key];
  const text = key.replace(/[_-]+/g, ' ').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : key;
}

/** Etiquetas legibles de los estados de procesamiento. */
export const STATUS_LABELS: Record<string, string> = {
  QUEUED: 'En cola',
  TRANSCRIBING: 'Transcribiendo',
  ANALYZING: 'Analizando',
  DONE: 'Listo',
  ERROR: 'Error',
};

/**
 * Nombre del ejecutivo a mostrar para una llamada.
 *
 * - Si está asignada a un ejecutivo registrado: su nombre completo.
 * - Si solo hay nombre detectado por la IA: ese nombre.
 * - Si aún no se procesó: "Sin identificar".
 */
export function callAgentName(call: {
  agent?: { name: string } | null;
  detected_agent_name?: string | null;
}): string {
  if (call.agent) return call.agent.name;
  if (call.detected_agent_name) return call.detected_agent_name;
  return 'Sin identificar';
}

