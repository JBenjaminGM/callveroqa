'use client';

import { dimensionLabel, scoreColor } from '@/lib/utils';
import type { RubricDimension } from '@/types';

/**
 * Ordena las dimensiones como están en la rúbrica.
 *
 * Los scores viajan en un objeto JSON, y el orden de sus claves no significa
 * nada. Sin esto, el formulario listaría las dimensiones en un orden y la
 * comparación en otro, para los mismos datos.
 */
export function orderByRubric(
  keys: string[],
  rubric?: RubricDimension[],
): string[] {
  if (!rubric?.length) return keys;
  const orden = new Map(rubric.map((d, i) => [d.dimension_key, i]));
  // Las dimensiones que ya no están en la rúbrica van al final, no se pierden.
  return [...keys].sort(
    (a, b) =>
      (orden.get(a) ?? Number.MAX_SAFE_INTEGER) -
      (orden.get(b) ?? Number.MAX_SAFE_INTEGER),
  );
}

/** Claves de las dimensiones que la rúbrica deja marcar como «no aplica». */
export function naAllowedKeys(rubric?: RubricDimension[]): Set<string> {
  return new Set(
    (rubric ?? []).filter((d) => d.allow_na).map((d) => d.dimension_key),
  );
}

/**
 * Las notas que se envían: sin las dimensiones marcadas «no aplica». Omitirlas
 * es lo que el backend entiende como «no aplica» — pondera solo lo puntuado.
 */
export function scoresToSend(
  scores: Record<string, number>,
  notApplicable: Set<string>,
): Record<string, number> {
  return Object.fromEntries(
    Object.entries(scores).filter(([k]) => !notApplicable.has(k)),
  );
}

/** Alterna una clave en un conjunto sin mutarlo (para usar en setState). */
export function toggled(set: Set<string>, key: string): Set<string> {
  const next = new Set(set);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return next;
}

/**
 * Formulario de puntuación por dimensión.
 *
 * Lo usan las dos formas de revisar —corregir una nota existente y puntuar a
 * ciegas— porque el gesto es el mismo; lo único que cambia es si se ve o no la
 * nota de la IA al lado.
 */
export function ScoreForm({
  keys,
  scores,
  onChange,
  reference,
  disabled,
  naAllowed,
  notApplicable,
  onToggleNA,
}: {
  /** Dimensiones a puntuar, en orden. */
  keys: string[];
  scores: Record<string, number>;
  onChange: (key: string, value: number) => void;
  /** Dimensiones que la rúbrica deja marcar como «no aplica». */
  naAllowed?: Set<string>;
  /** Las marcadas ahora mismo como «no aplica»: no se puntúan ni se envían. */
  notApplicable?: Set<string>;
  onToggleNA?: (key: string) => void;
  /**
   * Nota de la IA para mostrar al lado de cada deslizador. Se omite en las
   * sesiones a ciegas: ahí no debe existir ninguna referencia.
   */
  reference?: Record<string, number> | null;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-4">
      {keys.map((key) => {
        const value = scores[key] ?? 0;
        const ref = reference?.[key];
        const delta = ref == null ? null : value - ref;
        const puedeNA = !!onToggleNA && !!naAllowed?.has(key);
        if (notApplicable?.has(key)) {
          return (
            <div
              key={key}
              className="flex flex-wrap items-center justify-between gap-2"
            >
              <span className="text-small text-text-primary">
                {dimensionLabel(key)}
              </span>
              <span className="flex items-center gap-3 text-small">
                <span className="text-text-muted">
                  No aplica{reference && ref == null ? ' (la IA tampoco la puntuó)' : ''}
                </span>
                {puedeNA && (
                  <button
                    type="button"
                    onClick={() => onToggleNA?.(key)}
                    disabled={disabled}
                    className="text-accent-primary hover:underline"
                  >
                    Puntuar
                  </button>
                )}
              </span>
            </div>
          );
        }
        return (
          <div key={key}>
            <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2">
              <label
                htmlFor={`score-${key}`}
                className="text-small text-text-primary"
              >
                {dimensionLabel(key)}
              </label>
              <span className="flex items-center gap-2 font-mono text-small tabular-nums">
                {puedeNA && (
                  <button
                    type="button"
                    onClick={() => onToggleNA?.(key)}
                    disabled={disabled}
                    className="font-sans text-text-muted hover:text-accent-primary"
                    title="Esta llamada no dio ocasión de evaluar esta categoría"
                  >
                    No aplica
                  </button>
                )}
                {reference && ref == null && (
                  <span className="text-text-muted">IA: no aplica</span>
                )}
                {ref != null && (
                  <span className="text-text-muted">IA {ref}</span>
                )}
                <span
                  className="font-semibold"
                  style={{ color: scoreColor(value) }}
                >
                  {value}
                </span>
                {delta != null && delta !== 0 && (
                  <span
                    className={
                      delta > 0
                        ? 'text-success'
                        : 'text-danger'
                    }
                  >
                    {delta > 0 ? '+' : ''}
                    {delta}
                  </span>
                )}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <input
                id={`score-${key}`}
                type="range"
                min={0}
                max={100}
                step={1}
                value={value}
                disabled={disabled}
                aria-label={dimensionLabel(key)}
                onChange={(e) => onChange(key, Number(e.target.value))}
                className="w-full accent-[var(--accent-primary)]"
              />
              <input
                type="number"
                min={0}
                max={100}
                value={value}
                disabled={disabled}
                aria-label={`${dimensionLabel(key)} (valor)`}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  if (Number.isFinite(n)) {
                    onChange(key, Math.max(0, Math.min(100, Math.round(n))));
                  }
                }}
                className="h-8 w-16 shrink-0 rounded-control border border-border
                           bg-bg-secondary px-2 text-right font-mono text-small
                           tabular-nums text-text-primary"
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
