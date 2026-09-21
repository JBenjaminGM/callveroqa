'use client';

import { OctagonX, Play } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { dimensionLabel, formatDuration } from '@/lib/utils';
import type { CriticalFailure, TranscriptionSegment } from '@/types';

/**
 * Chips que llevan al momento exacto de la llamada en que se apoya una nota.
 * Una nota sin evidencia no se puede discutir ni usar para coaching; con ella,
 * el jefe escucha los cinco segundos que importan en lugar de la llamada entera.
 */
export function EvidenceChips({
  segments,
  transcriptSegments,
  onJump,
}: {
  segments: number[];
  transcriptSegments: TranscriptionSegment[];
  onJump: (index: number) => void;
}) {
  const validos = segments.filter((i) => transcriptSegments[i]);
  if (validos.length === 0) return null;
  return (
    <span className="inline-flex flex-wrap gap-1.5">
      {validos.map((i) => (
        <button
          key={i}
          type="button"
          onClick={() => onJump(i)}
          title={transcriptSegments[i].text}
          className="press-feedback inline-flex items-center gap-1 rounded-control
                     bg-bg-accent px-2 py-0.5 font-mono text-[12px] text-text-secondary
                     transition-colors hover:bg-rust-soft hover:text-text-primary"
        >
          <Play size={10} aria-hidden />
          {formatDuration(transcriptSegments[i].start)}
        </button>
      ))}
    </span>
  );
}

/**
 * Aviso de llamada suspendida por criterio crítico (auto-fail). Enseña qué
 * criterio se incumplió, por qué, dónde, y la nota que habría tenido: suspender
 * sin explicar sería tan opaco como no suspender.
 */
export function CriticalFailuresCard({
  failures,
  uncappedScore,
  transcriptSegments,
  onJump,
}: {
  failures: CriticalFailure[];
  uncappedScore?: number | null;
  transcriptSegments: TranscriptionSegment[];
  onJump: (index: number) => void;
}) {
  return (
    <Card className="border-danger/30 bg-danger/10">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-2 text-h3 text-danger">
          <OctagonX size={20} aria-hidden />
          Llamada suspendida por criterio crítico
        </p>
        {uncappedScore != null && (
          <span className="text-small text-text-secondary">
            Nota sin penalizar:{' '}
            <span className="font-mono font-semibold text-text-primary">
              {uncappedScore}
            </span>
          </span>
        )}
      </div>
      <ul className="flex flex-col gap-2.5">
        {failures.map((f, i) => (
          <li key={i} className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-body font-semibold text-text-primary">
                {f.criterion}
                <span className="ml-2 text-small font-normal text-text-muted">
                  {dimensionLabel(f.dimension)}
                </span>
              </p>
              {f.reason && (
                <p className="text-small text-text-secondary">{f.reason}</p>
              )}
            </div>
            {f.segment != null && (
              <EvidenceChips
                segments={[f.segment]}
                transcriptSegments={transcriptSegments}
                onJump={onJump}
              />
            )}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-small text-text-muted">
        Un criterio crítico incumplido deja la nota global en 0, sin importar el
        resto. Se definen en Configuración → Rúbrica.
      </p>
    </Card>
  );
}
