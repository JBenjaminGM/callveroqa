'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Check, EyeOff, Scale, TrendingUp } from 'lucide-react';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/input';
import { EmptyState, ErrorState, Skeleton, Spinner } from '@/components/ui/feedback';
import { SectionHeader } from '@/components/ui/section';
import { TranscriptPlayer } from '@/components/calls/transcript-player';
import {
  ScoreForm,
  naAllowedKeys,
  orderByRubric,
  scoresToSend,
  toggled,
} from '@/components/calibration/score-form';
import { ScoreGauge } from '@/components/dashboard/viz';
import {
  useAgreement,
  useBlindCall,
  useCalibrationQueue,
  useRubric,
  useSaveReview,
} from '@/lib/queries';
import { getErrorMessage } from '@/lib/api';
import { cn, dimensionLabel, formatDate, formatDuration, scoreColor } from '@/lib/utils';
import type { Review } from '@/types';

type Pestana = 'sesion' | 'acuerdo';

/**
 * Calibración: puntuar a ciegas y medir el acuerdo con la IA.
 *
 * Calibrar, en control de calidad, significa que varios evaluadores puntúan la
 * misma llamada sin verse entre ellos y después se compara la diferencia. Aquí
 * los dos evaluadores son la IA y el jefe.
 */
export default function CalibracionPage() {
  const [pestana, setPestana] = useState<Pestana>('sesion');

  return (
    <>
      <Header title="Calibración" />
      <main className="flex-1 overflow-y-auto p-6">
        <SectionHeader
          eyebrow="acuerdo ia-humano"
          title={
            <>
              Calibrar la <span className="hl">rúbrica</span>
            </>
          }
          description="Puntúa una llamada sin ver la nota de la IA y compara después. Donde más discrepéis, el criterio está mal escrito."
        />

        <Tabs valor={pestana} onCambio={setPestana} />

        {pestana === 'sesion' ? <SesionCiega /> : <PanelDeAcuerdo />}
      </main>
    </>
  );
}

const PESTANAS: { id: Pestana; label: string; icon: React.ReactNode }[] = [
  { id: 'sesion', label: 'Sesión a ciegas', icon: <EyeOff size={16} /> },
  { id: 'acuerdo', label: 'Panel de acuerdo', icon: <TrendingUp size={16} /> },
];

/**
 * Pestañas con el subrayado deslizante.
 *
 * Con un `border-bottom` por pestaña el color transiciona pero la línea salta
 * de sitio, que es el detalle que delata una pestaña hecha deprisa. Aquí el
 * subrayado es un único elemento que se mueve, midiendo el botón activo.
 */
function Tabs({
  valor,
  onCambio,
}: {
  valor: Pestana;
  onCambio: (p: Pestana) => void;
}) {
  const refs = useRef(new Map<Pestana, HTMLButtonElement>());
  const [marca, setMarca] = useState<{ left: number; width: number } | null>(
    null,
  );

  // Se remide también al redimensionar: el ancho de cada pestaña depende del
  // texto, y sin esto el subrayado se queda desalineado al cambiar de tamaño.
  useEffect(() => {
    function medir() {
      const el = refs.current.get(valor);
      if (el) setMarca({ left: el.offsetLeft, width: el.offsetWidth });
    }
    medir();
    window.addEventListener('resize', medir);
    return () => window.removeEventListener('resize', medir);
  }, [valor]);

  return (
    <div
      role="tablist"
      className="relative mb-6 mt-4 flex gap-1 border-b border-border"
    >
      {PESTANAS.map(({ id, label, icon }) => {
        const activa = valor === id;
        return (
          <button
            key={id}
            ref={(el) => {
              if (el) refs.current.set(id, el);
            }}
            type="button"
            role="tab"
            aria-selected={activa}
            onClick={() => onCambio(id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 text-body',
              'transition-colors duration-ui ease-out-strong',
              activa
                ? 'font-semibold text-accent-primary'
                : 'text-text-secondary hover:text-text-primary',
            )}
          >
            {icon}
            {label}
          </button>
        );
      })}

      {/* El subrayado. Se mueve con transform, que no provoca reflujo, y solo
          aparece cuando ya se ha medido, para no deslizar desde la nada. */}
      {marca && (
        <span
          aria-hidden
          className="absolute -bottom-px left-0 h-0.5 bg-rust
                     transition-transform duration-ui ease-out-strong"
          style={{
            width: marca.width,
            transform: `translateX(${marca.left}px)`,
          }}
        />
      )}
    </div>
  );
}

/* =========================== Sesión a ciegas =========================== */

function SesionCiega() {
  const { data: cola, isLoading, error } = useCalibrationQueue(20);
  const { data: rubrica } = useRubric();
  const [callId, setCallId] = useState<number | null>(null);
  const [resultado, setResultado] = useState<Review | null>(null);

  // Memorizado: es una dependencia de efecto en <Puntuacion>, y un array nuevo
  // en cada render lo dispararía siempre.
  const dimensiones = useMemo(
    () => (rubrica ?? []).map((d) => d.dimension_key),
    [rubrica],
  );

  const pendientes = useMemo(
    () => (cola ?? []).filter((c) => c.id !== resultado?.call_id),
    [cola, resultado],
  );

  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <ErrorState message={getErrorMessage(error)} />;

  // Acaba de puntuar: se revela la comparación.
  if (resultado) {
    return (
      <Revelacion
        review={resultado}
        siguiente={pendientes[0]?.id ?? null}
        onSiguiente={(id) => {
          setResultado(null);
          setCallId(id);
        }}
      />
    );
  }

  if (callId != null) {
    return (
      <Puntuacion
        callId={callId}
        dimensiones={dimensiones}
        onCancelar={() => setCallId(null)}
        onGuardada={setResultado}
      />
    );
  }

  if (!cola?.length) {
    return (
      <EmptyState
        icon={<Scale size={40} />}
        title="No queda nada por calibrar"
        description="Todas las llamadas analizadas ya tienen revisión humana. Sube llamadas nuevas para seguir calibrando."
        action={
          <Link href="/calls/new">
            <Button variant="secondary">Subir llamadas</Button>
          </Link>
        }
      />
    );
  }

  return (
    <Card>
      <CardTitle className="mb-1">Llamadas pendientes de calibrar</CardTitle>
      <p className="mb-4 text-small text-text-secondary">
        Al abrir una, su nota no viaja al navegador: puntúas sin referencia y la
        comparación aparece solo cuando guardas.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-small">
          <thead>
            <tr className="border-b border-border text-text-muted">
              <th className="py-2 text-left font-medium">Llamada</th>
              <th className="py-2 text-left font-medium">Ejecutivo</th>
              <th className="py-2 text-left font-medium">Campaña</th>
              <th className="py-2 text-left font-medium">Fecha</th>
              <th className="py-2 text-right font-medium">Duración</th>
              <th className="py-2" />
            </tr>
          </thead>
          <tbody>
            {cola.map((c) => (
              <tr key={c.id} className="border-b border-border/60 last:border-0">
                <td className="py-2.5 font-mono text-text-secondary">#{c.id}</td>
                <td className="py-2.5 text-text-primary">
                  {c.agent_name ?? 'Sin identificar'}
                </td>
                <td className="py-2.5 text-text-secondary">
                  {c.campaign ?? '—'}
                </td>
                <td className="py-2.5 text-text-secondary">
                  {c.call_date ? formatDate(c.call_date) : '—'}
                </td>
                <td className="py-2.5 text-right font-mono tabular-nums text-text-secondary">
                  {formatDuration(c.duration_seconds)}
                </td>
                <td className="py-2.5 text-right">
                  <Button
                    size="sm"
                    onClick={() => setCallId(c.id)}
                    disabled={!rubrica?.length}
                  >
                    <EyeOff size={16} />
                    Puntuar a ciegas
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

/** Pantalla de puntuación: transcripción y audio, sin ninguna nota a la vista. */
function Puntuacion({
  callId,
  dimensiones,
  onCancelar,
  onGuardada,
}: {
  callId: number;
  dimensiones: string[];
  onCancelar: () => void;
  onGuardada: (review: Review) => void;
}) {
  const { data: call, isLoading, error } = useBlindCall(callId);
  const save = useSaveReview();
  // Se arranca en 50 y no en la nota de la IA: cualquier valor previo sería
  // exactamente el anclaje que la sesión a ciegas trata de evitar.
  const [scores, setScores] = useState<Record<string, number>>(() =>
    Object.fromEntries(dimensiones.map((k) => [k, 50])),
  );
  const [comment, setComment] = useState('');
  // Aparte de las notas: así el efecto de abajo, que rellena las dimensiones
  // que faltan, no puede «resucitar» una marcada como no aplica.
  const [noAplica, setNoAplica] = useState<Set<string>>(() => new Set());
  const { data: rubrica } = useRubric();

  // Si la rúbrica termina de cargar después de abrir la llamada, sus dimensiones
  // se incorporan aquí. Sin esto el formulario se quedaría vacío y guardar
  // fallaría, que es justo el caso que nadie prueba a mano.
  useEffect(() => {
    setScores((prev) => {
      const faltan = dimensiones.filter((k) => !(k in prev));
      if (!faltan.length) return prev;
      return { ...prev, ...Object.fromEntries(faltan.map((k) => [k, 50])) };
    });
  }, [dimensiones]);

  const claves = dimensiones.length ? dimensiones : Object.keys(scores);

  async function onGuardar() {
    const review = await save.mutateAsync({
      callId,
      dimension_scores: scoresToSend(scores, noAplica),
      comment: comment.trim() || null,
      blind: true,
    });
    onGuardada(review);
  }

  if (isLoading) return <Skeleton className="h-96" />;
  if (error) return <ErrorState message={getErrorMessage(error)} />;
  if (!call) return null;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="flex flex-col gap-4">
        <Card>
          <CardTitle className="mb-1">Llamada #{call.id}</CardTitle>
          <p className="text-small text-text-secondary">
            {call.agent_name ?? 'Sin identificar'}
            {call.campaign ? ` · ${call.campaign}` : ''} ·{' '}
            {formatDuration(call.duration_seconds)}
          </p>
          <p
            className="mt-3 flex items-center gap-2 rounded-control bg-bg-accent
                       px-3 py-2 text-small text-text-secondary"
          >
            <EyeOff size={16} className="shrink-0 text-accent-primary" />
            La nota de la IA no se ha descargado. Aparecerá al guardar.
          </p>
        </Card>

        {call.transcription && (
          <TranscriptPlayer
            callId={call.id}
            transcription={call.transcription}
            audioFilename={call.audio_filename}
          />
        )}
      </div>

      <Card className="h-fit">
        <CardTitle className="mb-1">Tu puntuación</CardTitle>
        <p className="mb-5 text-small text-text-secondary">
          Puntúa cada dimensión de 0 a 100. El score global lo pondera la
          plataforma con los pesos de la rúbrica.
        </p>

        <ScoreForm
          keys={claves}
          scores={scores}
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
            htmlFor="blind-comment"
            className="mb-1.5 block text-small text-text-secondary"
          >
            Notas de la evaluación
          </label>
          <Textarea
            id="blind-comment"
            rows={3}
            value={comment}
            disabled={save.isPending}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Qué te ha llevado a puntuar así."
          />
        </div>

        {save.isError && (
          <div className="mt-3">
            <ErrorState message={getErrorMessage(save.error)} />
          </div>
        )}

        <div className="mt-5 flex items-center gap-3">
          <Button onClick={onGuardar} disabled={save.isPending}>
            {save.isPending ? <Spinner /> : <Check size={16} />}
            Guardar y comparar
          </Button>
          <Button variant="ghost" onClick={onCancelar} disabled={save.isPending}>
            Volver a la cola
          </Button>
        </div>
      </Card>
    </div>
  );
}

/** El momento de la revelación: tu nota frente a la de la IA. */
function Revelacion({
  review,
  siguiente,
  onSiguiente,
}: {
  review: Review;
  siguiente: number | null;
  onSiguiente: (id: number | null) => void;
}) {
  const { data: rubrica } = useRubric();
  const ia = review.ai_dimension_scores ?? {};
  const claves = orderByRubric(Object.keys(review.dimension_scores), rubrica);
  const delta = review.global_delta ?? 0;

  // El orden de la revelación: primero tu nota, después la de la IA y, cuando
  // los dos anillos ya han barrido, el remate — la diferencia. Contarlo todo a
  // la vez desperdicia el único momento del producto que merece una pausa.
  const retardo = (ms: number) =>
    ({ '--reveal-delay': `${ms}ms` }) as React.CSSProperties;

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardTitle className="mb-4">
          Llamada #{review.call_id} · comparación
        </CardTitle>
        <div className="flex flex-wrap items-center justify-center gap-10">
          <div
            className="reveal-item flex flex-col items-center gap-2"
            style={retardo(0)}
          >
            <span className="destacado text-[11px] text-text-muted">tu nota</span>
            <ScoreGauge value={review.global_score} decimals={0} size={132} />
          </div>
          <div
            className="reveal-item flex flex-col items-center gap-1"
            style={retardo(380)}
          >
            <span className="destacado text-[11px] text-text-muted">
              diferencia
            </span>
            <span className="font-mono text-[40px] font-semibold leading-none tabular-nums text-accent-primary">
              {delta > 0 ? '+' : ''}
              {delta}
            </span>
            <span className="max-w-[180px] text-center text-small text-text-secondary">
              {Math.abs(delta) <= 5
                ? 'Estáis calibrados en esta llamada.'
                : delta < 0
                  ? 'La IA fue más benévola que tú.'
                  : 'La IA fue más severa que tú.'}
            </span>
          </div>
          <div
            className="reveal-item flex flex-col items-center gap-2"
            style={retardo(160)}
          >
            <span className="destacado text-[11px] text-text-muted">la IA</span>
            <ScoreGauge
              value={review.ai_global_score ?? 0}
              decimals={0}
              size={132}
            />
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle className="mb-4">Dimensión a dimensión</CardTitle>
        <div className="flex flex-col gap-3">
          {claves.map((key, i) => {
            const humano = review.dimension_scores[key];
            const maquina = ia[key];
            const d = review.dimension_deltas?.[key];
            // 40 ms entre barras: suficiente para leerse como cascada, poco
            // para que la última se haga esperar.
            const espera = 460 + i * 30;
            return (
              <div key={key}>
                <div className="mb-1 flex justify-between text-small">
                  <span className="text-text-primary">{dimensionLabel(key)}</span>
                  <span className="flex items-center gap-3 font-mono tabular-nums">
                    <span className="text-text-muted">IA {maquina ?? '—'}</span>
                    <span
                      className="font-semibold"
                      style={{ color: scoreColor(humano) }}
                    >
                      Tú {humano}
                    </span>
                    {d != null && (
                      <span
                        className={
                          d === 0
                            ? 'text-text-muted'
                            : Math.abs(d) > 10
                              ? 'text-danger'
                              : 'text-warning'
                        }
                      >
                        {d > 0 ? '+' : ''}
                        {d}
                      </span>
                    )}
                  </span>
                </div>
                <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-bg-accent">
                  <div
                    className="bar-grow h-full rounded-full"
                    style={{
                      width: `${humano}%`,
                      background: scoreColor(humano),
                      ...retardo(espera),
                    }}
                  />
                  {maquina != null && (
                    <span
                      className="reveal-item absolute top-0 h-full w-0.5 bg-ink/60"
                      style={{ left: `${maquina}%`, ...retardo(espera + 120) }}
                      title={`IA: ${maquina}`}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <p className="mt-4 text-small text-text-muted">
          La barra es tu nota; la marca vertical, la de la IA.
        </p>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          onClick={() => onSiguiente(siguiente)}
          disabled={siguiente == null}
        >
          <ArrowRight size={16} />
          {siguiente == null ? 'No quedan llamadas' : 'Siguiente llamada'}
        </Button>
        <Link href={`/calls/${review.call_id}`}>
          <Button variant="secondary">Ver la llamada completa</Button>
        </Link>
        <Button variant="ghost" onClick={() => onSiguiente(null)}>
          Volver a la cola
        </Button>
      </div>
    </div>
  );
}

/* =========================== Panel de acuerdo =========================== */

function PanelDeAcuerdo() {
  const [period, setPeriod] = useState('30d');
  const [blindOnly, setBlindOnly] = useState(false);
  const { data, isLoading, error } = useAgreement({
    period,
    blind_only: blindOnly,
  });

  if (isLoading) return <Skeleton className="h-64" />;
  if (error) return <ErrorState message={getErrorMessage(error)} />;

  const filtros = (
    <div className="mb-6 flex flex-wrap items-center gap-3">
      <Select
        value={period}
        onChange={(e) => setPeriod(e.target.value)}
        className="w-40"
        aria-label="Periodo"
      >
        <option value="7d">7 días</option>
        <option value="30d">30 días</option>
        <option value="90d">90 días</option>
        <option value="all">Todo</option>
      </Select>
      <label className="flex items-center gap-2 text-small text-text-secondary">
        <input
          type="checkbox"
          checked={blindOnly}
          onChange={(e) => setBlindOnly(e.target.checked)}
          className="accent-[var(--accent-primary)]"
        />
        Solo revisiones a ciegas
      </label>
    </div>
  );

  if (!data || data.reviews_count === 0) {
    return (
      <>
        {filtros}
        <EmptyState
          icon={<Scale size={40} />}
          title="Todavía no hay con qué comparar"
          description="El panel necesita al menos una llamada con nota de la IA y revisión humana. Empieza por una sesión a ciegas."
        />
      </>
    );
  }

  const peor = data.dimensions[0];

  return (
    <>
      {filtros}

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <Kpi
          etiqueta="llamadas comparadas"
          valor={String(data.reviews_count)}
          nota={data.blind_only ? 'solo a ciegas' : 'todas las revisiones'}
        />
        <Kpi
          etiqueta="acuerdo"
          valor={data.agreement_pct == null ? '—' : `${data.agreement_pct}%`}
          nota={`diferencia ≤ ${data.tolerance} puntos`}
        />
        <Kpi
          etiqueta="desviación media"
          valor={`${data.mean_abs_diff}`}
          nota="puntos, en valor absoluto"
        />
        <Kpi
          etiqueta="sesgo"
          valor={`${(data.bias ?? 0) > 0 ? '+' : ''}${data.bias ?? 0}`}
          nota={
            (data.bias ?? 0) < 0
              ? 'la IA puntúa más alto'
              : (data.bias ?? 0) > 0
                ? 'la IA puntúa más bajo'
                : 'sin desvío sistemático'
          }
        />
      </div>

      {peor && peor.count > 0 && peor.mean_abs_diff > data.tolerance && (
        <Card className="mb-6 ring-1 ring-warning/40">
          <CardTitle className="mb-1">
            Revisa el criterio «{peor.dimension_name}»
          </CardTitle>
          <p className="text-small text-text-secondary">
            Es donde más discrepáis: {peor.mean_abs_diff} puntos de desviación
            media frente a los {data.mean_abs_diff} del conjunto. Cuando una
            dimensión se desvía tanto más que el resto, lo habitual no es que la
            IA falle, sino que ese criterio de la rúbrica admita dos lecturas.{' '}
            <Link
              href="/settings"
              className="text-accent-primary hover:underline"
            >
              Reescribir la rúbrica
            </Link>
            .
          </p>
        </Card>
      )}

      <Card>
        <CardTitle className="mb-1">Acuerdo por dimensión</CardTitle>
        <p className="mb-4 text-small text-text-secondary">
          Ordenadas de peor a mejor calibrada. El sesgo puede cancelarse entre
          llamadas; la desviación media, no: por eso manda ella.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-small">
            <thead>
              <tr className="border-b border-border text-text-muted">
                <th className="py-2 text-left font-medium">Dimensión</th>
                <th className="py-2 text-right font-medium">n</th>
                <th className="py-2 text-right font-medium">IA</th>
                <th className="py-2 text-right font-medium">Humano</th>
                <th className="py-2 text-right font-medium">Sesgo</th>
                <th className="py-2 text-right font-medium">Desv. media</th>
                <th className="py-2 text-right font-medium">Acuerdo</th>
              </tr>
            </thead>
            <tbody>
              {data.dimensions.map((d) => (
                <tr
                  key={d.dimension_key}
                  className="border-b border-border/60 last:border-0"
                >
                  <td className="py-2.5 text-text-primary">{d.dimension_name}</td>
                  <td className="py-2.5 text-right font-mono tabular-nums text-text-muted">
                    {d.count}
                  </td>
                  <td className="py-2.5 text-right font-mono tabular-nums text-text-secondary">
                    {d.ai_avg ?? '—'}
                  </td>
                  <td className="py-2.5 text-right font-mono tabular-nums text-text-secondary">
                    {d.human_avg ?? '—'}
                  </td>
                  <td className="py-2.5 text-right font-mono tabular-nums text-text-secondary">
                    {d.bias == null
                      ? '—'
                      : `${d.bias > 0 ? '+' : ''}${d.bias}`}
                  </td>
                  <td
                    className="py-2.5 text-right font-mono font-semibold tabular-nums"
                    style={{
                      color:
                        d.mean_abs_diff > data.tolerance * 2
                          ? 'var(--danger)'
                          : d.mean_abs_diff > data.tolerance
                            ? 'var(--warning)'
                            : 'var(--success)',
                    }}
                  >
                    {d.mean_abs_diff}
                  </td>
                  <td className="py-2.5 text-right font-mono tabular-nums text-text-secondary">
                    {d.agreement_pct == null ? '—' : `${d.agreement_pct}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

function Kpi({
  etiqueta,
  valor,
  nota,
}: {
  etiqueta: string;
  valor: string;
  nota: string;
}) {
  return (
    <Card>
      <span className="destacado text-[11px] text-text-muted">{etiqueta}</span>
      <p className="mt-1 font-mono text-h1 font-semibold tabular-nums text-text-primary">
        {valor}
      </p>
      <p className="mt-0.5 text-small text-text-muted">{nota}</p>
    </Card>
  );
}
