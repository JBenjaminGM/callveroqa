'use client';

import { useState } from 'react';
import { Check, Pencil, Scale, Trash2, X } from 'lucide-react';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';
import { Spinner, ErrorState } from '@/components/ui/feedback';
import {
  ScoreForm,
  naAllowedKeys,
  orderByRubric,
  scoresToSend,
  toggled,
} from '@/components/calibration/score-form';
import { getErrorMessage } from '@/lib/api';
import { isManager, useAuthStore } from '@/lib/auth';
import { useDeleteReview, useRubric, useSaveReview } from '@/lib/queries';
import { dimensionLabel, formatDateTime, scoreColor } from '@/lib/utils';
import type { CallDetail } from '@/types';

/**
 * Revisión humana de una nota, en el detalle de la llamada.
 *
 * La nota de la IA no se sustituye en ningún momento: se muestran las dos y la
 * diferencia entre ambas. Cuando el jefe corrige, lo que aporta de valor no es
 * el número nuevo sino el motivo, así que el campo del motivo va siempre a la
 * vista y no escondido tras un desplegable.
 */
export function ReviewCard({ call }: { call: CallDetail }) {
  const user = useAuthStore((s) => s.user);
  const puedeRevisar = isManager(user);
  const review = call.review ?? null;
  const [editando, setEditando] = useState(false);

  if (!call.analysis) return null;

  if (editando) {
    return (
      <ReviewForm
        call={call}
        onClose={() => setEditando(false)}
      />
    );
  }

  if (!review) {
    if (!puedeRevisar) return null;
    return (
      <Card className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <CardTitle className="mb-1 flex items-center gap-2">
            <Scale size={18} className="text-accent-primary" />
            Revisión humana
          </CardTitle>
          <p className="max-w-2xl text-small text-text-secondary">
            La IA puntuó esta llamada con un{' '}
            <strong className="text-text-primary">
              {call.analysis.global_score}
            </strong>
            . Si no estás de acuerdo, corrígela: tu nota se guarda junto a la
            suya, sin reemplazarla, y la diferencia entre ambas alimenta el
            panel de calibración.
          </p>
        </div>
        <Button onClick={() => setEditando(true)}>
          <Pencil size={16} />
          Revisar esta nota
        </Button>
      </Card>
    );
  }

  return (
    <ReviewComparison
      call={call}
      onEdit={puedeRevisar ? () => setEditando(true) : undefined}
    />
  );
}

/* ------------------------------ Comparación ------------------------------ */

function ReviewComparison({
  call,
  onEdit,
}: {
  call: CallDetail;
  onEdit?: () => void;
}) {
  const review = call.review!;
  const remove = useDeleteReview();
  const { data: rubrica } = useRubric();
  const ia = review.ai_dimension_scores ?? call.analysis?.dimension_scores ?? {};
  const claves = orderByRubric(Object.keys(review.dimension_scores), rubrica);

  async function onDelete() {
    if (
      !confirm(
        '¿Retirar la revisión humana? La nota de la IA no se ve afectada.',
      )
    ) {
      return;
    }
    await remove.mutateAsync(call.id);
  }

  return (
    <Card className="ring-1 ring-accent-primary/30">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <CardTitle className="mb-1 flex items-center gap-2">
            <Scale size={18} className="text-accent-primary" />
            Revisión humana
            {review.blind && (
              <span
                className="rounded-control bg-accent-primary/15 px-2 py-0.5
                           text-[11px] font-medium text-accent-primary"
              >
                A ciegas
              </span>
            )}
          </CardTitle>
          <p className="text-small text-text-secondary">
            {review.reviewer_name ?? 'Revisor'} ·{' '}
            {formatDateTime(review.updated_at ?? review.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onEdit && (
            <Button variant="secondary" size="sm" onClick={onEdit}>
              <Pencil size={16} />
              Editar
            </Button>
          )}
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              disabled={remove.isPending}
              title="Retirar la revisión"
            >
              <Trash2 size={16} />
            </Button>
          )}
        </div>
      </div>

      {/* Los dos globales, uno al lado del otro. */}
      <div className="mb-5 grid grid-cols-3 gap-3">
        <ScoreBox etiqueta="IA" valor={review.ai_global_score ?? null} />
        <ScoreBox etiqueta="Humano" valor={review.global_score} />
        <div className="flex flex-col items-center justify-center rounded-card bg-bg-secondary p-3">
          <span className="destacado text-[11px] text-text-muted">
            diferencia
          </span>
          <span
            className="font-mono text-h2 font-semibold tabular-nums"
            style={{
              color:
                (review.global_delta ?? 0) === 0
                  ? 'var(--text-secondary)'
                  : 'var(--accent-primary)',
            }}
          >
            {(review.global_delta ?? 0) > 0 ? '+' : ''}
            {review.global_delta ?? 0}
          </span>
        </div>
      </div>

      {/* Dimensión a dimensión. */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] text-small">
          <thead>
            <tr className="border-b border-border text-text-muted">
              <th className="py-2 text-left font-medium">Dimensión</th>
              <th className="py-2 text-right font-medium">IA</th>
              <th className="py-2 text-right font-medium">Humano</th>
              <th className="py-2 text-right font-medium">Δ</th>
            </tr>
          </thead>
          <tbody>
            {claves.map((key) => {
              const humano = review.dimension_scores[key];
              const maquina = ia[key];
              const delta = review.dimension_deltas?.[key];
              return (
                <tr key={key} className="border-b border-border/60 last:border-0">
                  <td className="py-2 text-text-primary">
                    {dimensionLabel(key)}
                  </td>
                  <td className="py-2 text-right font-mono tabular-nums text-text-secondary">
                    {maquina ?? '—'}
                  </td>
                  <td
                    className="py-2 text-right font-mono font-semibold tabular-nums"
                    style={{ color: scoreColor(humano) }}
                  >
                    {humano}
                  </td>
                  <td className="py-2 text-right font-mono tabular-nums">
                    {delta == null ? (
                      <span className="text-text-muted">—</span>
                    ) : delta === 0 ? (
                      <span className="text-text-muted">0</span>
                    ) : (
                      <span
                        className={delta > 0 ? 'text-success' : 'text-danger'}
                      >
                        {delta > 0 ? '+' : ''}
                        {delta}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {review.comment && (
        <div className="mt-4 rounded-card bg-bg-secondary p-3">
          <p className="destacado mb-1 text-[11px] text-text-muted">
            motivo de la corrección
          </p>
          <p className="text-body text-text-secondary">{review.comment}</p>
        </div>
      )}
    </Card>
  );
}

function ScoreBox({ etiqueta, valor }: { etiqueta: string; valor: number | null }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card bg-bg-secondary p-3">
      <span className="destacado text-[11px] text-text-muted">{etiqueta}</span>
      <span
        className="font-mono text-h2 font-semibold tabular-nums"
        style={{ color: valor == null ? 'var(--text-muted)' : scoreColor(valor) }}
      >
        {valor ?? '—'}
      </span>
    </div>
  );
}

/* -------------------------------- Formulario ------------------------------ */

function ReviewForm({ call, onClose }: { call: CallDetail; onClose: () => void }) {
  const save = useSaveReview();
  const { data: rubrica } = useRubric();
  const ia = call.analysis?.dimension_scores ?? {};
  const iaNoAplica = call.analysis?.not_applicable ?? [];
  const previa = call.review?.dimension_scores;

  // Se parte de la nota que ya hubiera; si es la primera revisión, de la de la
  // IA. Empezar en cero obligaría a mover las siete dimensiones para corregir
  // una sola. Las que no aplicaban arrancan en 50 por si se deciden puntuar.
  const [scores, setScores] = useState<Record<string, number>>(() => ({
    ...Object.fromEntries(iaNoAplica.map((k) => [k, 50])),
    ...ia,
    ...(previa ?? {}),
  }));
  // «No aplica» de partida: lo que dijo la IA o, si ya hubo revisión, lo que
  // esa revisión dejó sin puntuar.
  const [noAplica, setNoAplica] = useState<Set<string>>(
    () =>
      new Set(
        previa
          ? [...Object.keys(ia), ...iaNoAplica].filter((k) => !(k in previa))
          : iaNoAplica,
      ),
  );
  const [comment, setComment] = useState(call.review?.comment ?? '');

  const claves = orderByRubric(
    Object.keys(ia).length || iaNoAplica.length
      ? [...Object.keys(ia), ...iaNoAplica]
      : Object.keys(scores),
    rubrica,
  );
  const aEnviar = scoresToSend(scores, noAplica);
  // Sin cambios = cada dimensión está como la dejó la IA: misma nota, o «no
  // aplica» en las mismas.
  const sinCambios = claves.every((k) =>
    noAplica.has(k) ? !(k in ia) : scores[k] === ia[k],
  );

  async function onSave() {
    await save.mutateAsync({
      callId: call.id,
      dimension_scores: aEnviar,
      comment: comment.trim() || null,
      // Editar desde el detalle nunca es a ciegas: la nota de la IA está a la
      // vista. Marcarla como ciega falsearía el panel de acuerdo.
      blind: false,
    });
    onClose();
  }

  return (
    <Card className="ring-1 ring-accent-primary/30">
      <CardTitle className="mb-1 flex items-center gap-2">
        <Scale size={18} className="text-accent-primary" />
        {call.review ? 'Editar la revisión' : 'Revisar esta nota'}
      </CardTitle>
      <p className="mb-5 text-small text-text-secondary">
        Ajusta las dimensiones en las que no estés de acuerdo con la IA. Su nota
        se conserva intacta: se guarda la tuya al lado.
      </p>

      <ScoreForm
        keys={claves}
        scores={scores}
        reference={ia}
        onChange={(key, value) =>
          setScores((prev) => ({ ...prev, [key]: value }))
        }
        disabled={save.isPending}
        naAllowed={naAllowedKeys(rubrica)}
        notApplicable={noAplica}
        onToggleNA={(key) => setNoAplica((prev) => toggled(prev, key))}
      />

      <div className="mt-5">
        <label
          htmlFor="review-comment"
          className="mb-1.5 block text-small text-text-secondary"
        >
          Motivo de la corrección
        </label>
        <Textarea
          id="review-comment"
          rows={3}
          value={comment}
          disabled={save.isPending}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Ej.: no confirmó el importe de la cuota antes de cerrar."
        />
      </div>

      {sinCambios && (
        <p className="mt-3 text-small text-text-muted">
          Todavía no has cambiado ninguna puntuación. Guardar así registra que
          estás de acuerdo con la IA, que también es un dato útil.
        </p>
      )}

      {save.isError && (
        <div className="mt-3">
          <ErrorState message={getErrorMessage(save.error)} />
        </div>
      )}

      <div className="mt-5 flex items-center gap-3">
        <Button
          onClick={onSave}
          disabled={save.isPending || Object.keys(aEnviar).length === 0}
        >
          {save.isPending ? <Spinner /> : <Check size={16} />}
          Guardar revisión
        </Button>
        <Button variant="ghost" onClick={onClose} disabled={save.isPending}>
          <X size={16} />
          Cancelar
        </Button>
      </div>
    </Card>
  );
}
