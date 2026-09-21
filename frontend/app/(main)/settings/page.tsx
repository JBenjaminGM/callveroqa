'use client';

import { useEffect, useState } from 'react';
import {
  Lock,
  OctagonX,
  Plus,
  Save,
  Scale,
  Trash2,
  Unlock,
} from 'lucide-react';
import {
  useRubric,
  useSettings,
  useUpdateRubric,
  useUpdateSettings,
} from '@/lib/queries';
import { getErrorMessage } from '@/lib/api';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { ErrorState, Skeleton, Spinner } from '@/components/ui/feedback';
import type { RubricDimensionInput } from '@/types';

const LANGUAGES = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'Inglés' },
  { code: 'pt', label: 'Portugués' },
  { code: 'fr', label: 'Francés' },
];

/**
 * Reparte 100 puntos entre las categorías tras mover una de ellas.
 *
 * Los pesos son relativos: el jefe dice «el saludo me importa el doble», no
 * «reparte cien puntos». Al subir uno, las demás ceden espacio manteniendo su
 * proporción entre sí; las que estén bloqueadas no se tocan.
 */
function repartir(
  dims: RubricDimensionInput[],
  indice: number,
  pesoPedido: number,
  bloqueadas: Set<number>,
): RubricDimensionInput[] {
  const fijo = dims.reduce(
    (acc, d, i) =>
      i !== indice && bloqueadas.has(i) ? acc + (Number(d.weight) || 0) : acc,
    0,
  );
  const disponible = Math.max(0, 100 - fijo);
  const peso = Math.min(Math.max(0, pesoPedido), disponible);
  const resto = disponible - peso;

  const ajustables = dims
    .map((_, i) => i)
    .filter((i) => i !== indice && !bloqueadas.has(i));
  const sumaAjustables = ajustables.reduce(
    (a, i) => a + (Number(dims[i].weight) || 0),
    0,
  );

  const repartidas = dims.map((d, i) => {
    if (i === indice) return { ...d, weight: peso };
    if (bloqueadas.has(i) || !ajustables.includes(i)) return d;
    // Sin nada que repartir proporcionalmente, se reparte a partes iguales.
    const cuota =
      sumaAjustables > 0
        ? (Number(d.weight) || 0) / sumaAjustables
        : 1 / ajustables.length;
    return { ...d, weight: resto * cuota };
  });

  return cuadrar(repartidas, ajustables.length ? ajustables : [indice]);
}

/** Redondea a dos decimales y deja la diferencia en la categoría más grande. */
function cuadrar(
  dims: RubricDimensionInput[],
  candidatas: number[],
): RubricDimensionInput[] {
  const redondeadas = dims.map((d) => ({
    ...d,
    weight: Math.round((Number(d.weight) || 0) * 100) / 100,
  }));
  const suma = redondeadas.reduce((a, d) => a + d.weight, 0);
  const sobra = Math.round((100 - suma) * 100) / 100;
  if (sobra === 0 || candidatas.length === 0) return redondeadas;

  const destino = candidatas.reduce((mejor, i) =>
    redondeadas[i].weight > redondeadas[mejor].weight ? i : mejor,
  );
  redondeadas[destino] = {
    ...redondeadas[destino],
    weight: Math.round((redondeadas[destino].weight + sobra) * 100) / 100,
  };
  return redondeadas;
}

/** Umbrales de QA configurables (coinciden con app_settings del backend). */
const QA_FIELDS = [
  {
    key: 'qa_target_score',
    label: 'Meta de score (verde)',
    hint: 'A partir de aquí se considera excelente.',
    min: 0,
    max: 100,
  },
  {
    key: 'qa_low_agent_threshold',
    label: 'Asesor «requiere atención» por debajo de',
    hint: 'Dispara alertas de bajo rendimiento.',
    min: 0,
    max: 100,
  },
  {
    key: 'qa_red_call_threshold',
    label: 'Llamada en banda roja por debajo de',
    hint: 'Marca las llamadas críticas.',
    min: 0,
    max: 100,
  },
  {
    key: 'qa_min_calls_ranking',
    label: 'Mínimo de llamadas para rankings',
    hint: 'Evita rankings con muestras muy pequeñas.',
    min: 1,
    max: 1000,
  },
  {
    key: 'qa_trend_drop_alert',
    label: 'Caída de score que dispara alerta (puntos)',
    hint: 'Detecta tendencias negativas.',
    min: 0,
    max: 100,
  },
] as const;

/** Página de configuración: rúbrica de evaluación (con subcategorías) e idioma. */
export default function SettingsPage() {
  const { data: rubric, isLoading: rubricLoading, error: rubricError } =
    useRubric();
  const { data: settings } = useSettings();
  const updateRubric = useUpdateRubric();
  const updateSettings = useUpdateSettings();

  // Estado local editable: la rúbrica completa (categorías + subcategorías).
  const [dims, setDims] = useState<RubricDimensionInput[]>([]);
  const [language, setLanguage] = useState('es');
  const [rubricMsg, setRubricMsg] = useState<string | null>(null);
  const [rubricErr, setRubricErr] = useState<string | null>(null);
  const [settingsMsg, setSettingsMsg] = useState<string | null>(null);

  // Umbrales / metas de QA configurables.
  const [qa, setQa] = useState<Record<string, number>>({});
  const [qaMsg, setQaMsg] = useState<string | null>(null);

  useEffect(() => {
    if (rubric) {
      setDims(
        rubric.map((d) => ({
          dimension_key: d.dimension_key,
          dimension_name: d.dimension_name,
          description: d.description ?? '',
          weight: Number(d.weight),
          criteria: (d.criteria ?? []).map((c) => ({
            name: c.name,
            enabled: c.enabled,
            critical: !!c.critical,
          })),
        })),
      );
    }
  }, [rubric]);

  useEffect(() => {
    if (settings) {
      setLanguage(settings.default_language);
      setQa({
        qa_target_score: settings.qa_target_score ?? 90,
        qa_low_agent_threshold: settings.qa_low_agent_threshold ?? 80,
        qa_red_call_threshold: settings.qa_red_call_threshold ?? 60,
        qa_min_calls_ranking: settings.qa_min_calls_ranking ?? 5,
        qa_trend_drop_alert: settings.qa_trend_drop_alert ?? 5,
      });
    }
  }, [settings]);

  const total = dims.reduce((a, d) => a + (Number(d.weight) || 0), 0);

  // Categorías cuyo peso el jefe quiere congelar mientras ajusta las demás.
  const [bloqueadas, setBloqueadas] = useState<Set<number>>(new Set());

  function alternarBloqueo(i: number) {
    setBloqueadas((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(i)) siguiente.delete(i);
      else siguiente.add(i);
      return siguiente;
    });
  }

  /** Cambia el peso de una categoría y reparte el resto entre las demás. */
  function cambiarPeso(i: number, valor: number) {
    setDims((ds) => repartir(ds, i, valor, bloqueadas));
  }

  function repartirPorIgual() {
    setDims((ds) => {
      if (ds.length === 0) return ds;
      const iguales = ds.map((d) => ({ ...d, weight: 100 / ds.length }));
      return cuadrar(iguales, ds.map((_, i) => i));
    });
    setBloqueadas(new Set());
  }

  // --- Helpers de edición ---
  function patchDim(i: number, patch: Partial<RubricDimensionInput>) {
    setDims((ds) => ds.map((d, j) => (j === i ? { ...d, ...patch } : d)));
  }
  function patchCriterion(
    i: number,
    ci: number,
    patch: Partial<{ name: string; enabled: boolean; critical: boolean }>,
  ) {
    setDims((ds) =>
      ds.map((d, j) =>
        j === i
          ? {
              ...d,
              criteria: d.criteria.map((c, k) =>
                k === ci ? { ...c, ...patch } : c,
              ),
            }
          : d,
      ),
    );
  }
  function addCriterion(i: number) {
    setDims((ds) =>
      ds.map((d, j) =>
        j === i
          ? {
              ...d,
              criteria: [...d.criteria, { name: '', enabled: true, critical: false }],
            }
          : d,
      ),
    );
  }
  function removeCriterion(i: number, ci: number) {
    setDims((ds) =>
      ds.map((d, j) =>
        j === i
          ? { ...d, criteria: d.criteria.filter((_, k) => k !== ci) }
          : d,
      ),
    );
  }
  function addDimension() {
    // La nueva entra con el peso medio y el resto cede espacio proporcionalmente,
    // para no dejar nunca la suma descuadrada.
    setDims((ds) => {
      const conNueva = [
        ...ds,
        { dimension_name: '', description: '', weight: 0, criteria: [] },
      ];
      const pesoInicial = conNueva.length > 1 ? 100 / conNueva.length : 100;
      return repartir(conNueva, conNueva.length - 1, pesoInicial, new Set());
    });
  }
  function removeDimension(i: number) {
    setDims((ds) => {
      const restantes = ds.filter((_, j) => j !== i);
      if (restantes.length === 0) return restantes;
      // El peso que se va se reparte entre las que quedan.
      return repartir(restantes, 0, Number(restantes[0].weight) || 0, new Set());
    });
    setBloqueadas(new Set());
  }

  async function saveRubric() {
    setRubricMsg(null);
    setRubricErr(null);
    if (dims.some((d) => !d.dimension_name.trim())) {
      setRubricErr('Todas las categorías deben tener nombre.');
      return;
    }
    const payload: RubricDimensionInput[] = dims.map((d) => ({
      dimension_key: d.dimension_key,
      dimension_name: d.dimension_name.trim(),
      description: d.description?.trim() || null,
      weight: Number(d.weight) || 0,
      criteria: d.criteria
        .filter((c) => c.name.trim())
        .map((c) => ({
          name: c.name.trim(),
          enabled: c.enabled,
          critical: !!c.critical,
        })),
    }));
    try {
      await updateRubric.mutateAsync(payload);
      setRubricMsg('Rúbrica actualizada. Aplica a las próximas llamadas.');
    } catch (err) {
      setRubricErr(getErrorMessage(err));
    }
  }

  async function saveLanguage() {
    setSettingsMsg(null);
    try {
      await updateSettings.mutateAsync({ default_language: language });
      setSettingsMsg('Idioma de análisis actualizado.');
    } catch (err) {
      setSettingsMsg(getErrorMessage(err));
    }
  }

  async function saveThresholds() {
    setQaMsg(null);
    try {
      await updateSettings.mutateAsync(qa);
      setQaMsg('Umbrales de QA actualizados.');
    } catch (err) {
      setQaMsg(getErrorMessage(err));
    }
  }

  return (
    <>
      <Header title="Configuración" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {/* Rúbrica */}
          <Card>
            <CardTitle className="mb-1">Rúbrica de evaluación</CardTitle>
            <p className="mb-4 text-small text-text-secondary">
              Define las categorías (con su peso %) y las subcategorías que la IA
              tendrá en cuenta. Activa/desactiva subcategorías, añade las tuyas o
              crea categorías nuevas. Mueve un peso y el resto se recoloca solo;
              usa el candado para fijar el que no quieras que cambie.
            </p>

            {rubricLoading && (
              <div className="flex flex-col gap-2">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20" />
                ))}
              </div>
            )}
            {rubricError && <ErrorState message={getErrorMessage(rubricError)} />}

            {!rubricLoading && (
              <div className="flex flex-col gap-4">
                {dims.map((dim, i) => (
                  <div
                    key={dim.dimension_key ?? `new-${i}`}
                    className="rounded-card border border-border bg-bg-secondary p-3"
                  >
                    {/* Cabecera: nombre + peso + candado + eliminar */}
                    <div className="mb-2 flex items-center gap-2">
                      <Input
                        value={dim.dimension_name}
                        placeholder="Nombre de la categoría"
                        onChange={(e) =>
                          patchDim(i, { dimension_name: e.target.value })
                        }
                        className="flex-1 font-semibold"
                      />
                      <div className="flex w-[86px] items-center gap-1">
                        <Input
                          type="number"
                          min={0}
                          max={100}
                          step="1"
                          value={Number(dim.weight).toFixed(
                            Number.isInteger(Number(dim.weight)) ? 0 : 2,
                          )}
                          onChange={(e) => cambiarPeso(i, Number(e.target.value))}
                          aria-label={`Peso de ${dim.dimension_name || 'la categoría'}`}
                        />
                        <span className="text-small text-text-muted">%</span>
                      </div>
                      <button
                        onClick={() => alternarBloqueo(i)}
                        title={
                          bloqueadas.has(i)
                            ? 'Peso fijo: no cambia al mover los demás'
                            : 'Fijar este peso'
                        }
                        aria-pressed={bloqueadas.has(i)}
                        className={
                          bloqueadas.has(i)
                            ? 'rounded-control p-2 text-rust transition-colors hover:bg-rust/10'
                            : 'rounded-control p-2 text-text-muted transition-colors hover:bg-bg-accent'
                        }
                      >
                        {bloqueadas.has(i) ? <Lock size={16} /> : <Unlock size={16} />}
                      </button>
                      <button
                        onClick={() => removeDimension(i)}
                        title="Eliminar categoría"
                        className="rounded-control p-2 text-text-muted transition-colors hover:bg-danger/10 hover:text-danger"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>

                    {/* Deslizador: mueve uno y los demás ceden espacio solos. */}
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Number(dim.weight)}
                      onChange={(e) => cambiarPeso(i, Number(e.target.value))}
                      disabled={bloqueadas.has(i)}
                      aria-label={`Ajustar el peso de ${dim.dimension_name || 'la categoría'}`}
                      className="mb-3 w-full accent-[var(--rust)] disabled:opacity-40"
                    />

                    {/* Subcategorías */}
                    <div className="flex flex-col gap-1.5 pl-1">
                      {dim.criteria.map((c, ci) => (
                        <div key={ci} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={c.enabled}
                            onChange={(e) =>
                              patchCriterion(i, ci, { enabled: e.target.checked })
                            }
                            className="accent-[var(--accent-primary)]"
                            title={c.enabled ? 'Activa' : 'Inactiva'}
                          />
                          <Input
                            value={c.name}
                            placeholder="Subcategoría a evaluar"
                            onChange={(e) =>
                              patchCriterion(i, ci, { name: e.target.value })
                            }
                            className={
                              c.enabled
                                ? 'flex-1 !py-1.5 text-small'
                                : 'flex-1 !py-1.5 text-small line-through opacity-60'
                            }
                          />
                          {/* Crítico = auto-fail: incumplirlo suspende la llamada (nota 0). */}
                          <button
                            type="button"
                            aria-pressed={!!c.critical}
                            onClick={() =>
                              patchCriterion(i, ci, { critical: !c.critical })
                            }
                            title={
                              c.critical
                                ? 'Crítico: si se incumple, la llamada queda suspendida (nota 0). Pulsa para quitarlo.'
                                : 'Marcar como crítico: incumplirlo suspenderá la llamada entera.'
                            }
                            className={
                              c.critical
                                ? 'press-feedback flex shrink-0 items-center gap-1 rounded-control bg-danger/15 px-2 py-1 text-small font-medium text-danger'
                                : 'press-feedback flex shrink-0 items-center gap-1 rounded-control px-2 py-1 text-small text-text-muted transition-colors hover:bg-bg-accent hover:text-text-secondary'
                            }
                          >
                            <OctagonX size={14} aria-hidden />
                            Crítico
                          </button>
                          <button
                            onClick={() => removeCriterion(i, ci)}
                            title="Quitar subcategoría"
                            className="rounded-control p-1.5 text-text-muted transition-colors hover:bg-danger/10 hover:text-danger"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                      <button
                        onClick={() => addCriterion(i)}
                        className="mt-1 flex w-fit items-center gap-1 text-small text-accent-primary transition-opacity hover:opacity-80"
                      >
                        <Plus size={14} />
                        Añadir subcategoría
                      </button>
                    </div>
                  </div>
                ))}

                <Button variant="secondary" onClick={addDimension}>
                  <Plus size={18} />
                  Añadir categoría
                </Button>

                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
                  <Button variant="ghost" size="sm" onClick={repartirPorIgual}>
                    <Scale size={16} />
                    Repartir por igual
                  </Button>
                  <span className="text-small text-text-muted">
                    Los pesos se reajustan solos para sumar{' '}
                    <span className="font-mono font-semibold text-success">
                      {total.toFixed(total % 1 === 0 ? 0 : 2)}%
                    </span>
                  </span>
                </div>

                {rubricErr && <ErrorState message={rubricErr} />}
                {rubricMsg && (
                  <p className="text-small text-success">{rubricMsg}</p>
                )}

                <div>
                  <Button onClick={saveRubric} disabled={updateRubric.isPending}>
                    {updateRubric.isPending ? <Spinner /> : <Save size={18} />}
                    Guardar rúbrica
                  </Button>
                </div>
              </div>
            )}
          </Card>

          {/* Idioma de análisis */}
          <Card>
            <CardTitle className="mb-1">Idioma de análisis</CardTitle>
            <p className="mb-4 text-small text-text-secondary">
              Idioma usado para transcribir y analizar las próximas llamadas.
            </p>
            <div className="flex items-end gap-3">
              <div className="w-52">
                <Label htmlFor="lang">Idioma</Label>
                <Select
                  id="lang"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.label}
                    </option>
                  ))}
                </Select>
              </div>
              <Button onClick={saveLanguage} disabled={updateSettings.isPending}>
                {updateSettings.isPending ? <Spinner /> : <Save size={18} />}
                Guardar
              </Button>
            </div>
            {settingsMsg && (
              <p className="mt-3 text-small text-success">{settingsMsg}</p>
            )}
          </Card>

          {/* Umbrales / metas de QA */}
          <Card>
            <CardTitle className="mb-1">Umbrales de calidad (QA)</CardTitle>
            <p className="mb-4 text-small text-text-secondary">
              Definen los colores, las alertas y los rankings del dashboard. Se
              aplican de inmediato a toda la analítica.
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {QA_FIELDS.map((f) => (
                <div key={f.key}>
                  <Label htmlFor={f.key}>{f.label}</Label>
                  <Input
                    id={f.key}
                    type="number"
                    min={f.min}
                    max={f.max}
                    value={qa[f.key] ?? ''}
                    onChange={(e) =>
                      setQa((q) => ({ ...q, [f.key]: Number(e.target.value) }))
                    }
                  />
                  <p className="mt-1 text-small text-text-muted">{f.hint}</p>
                </div>
              ))}
            </div>
            <div className="mt-4">
              <Button onClick={saveThresholds} disabled={updateSettings.isPending}>
                {updateSettings.isPending ? <Spinner /> : <Save size={18} />}
                Guardar umbrales
              </Button>
            </div>
            {qaMsg && <p className="mt-3 text-small text-success">{qaMsg}</p>}
          </Card>

          {/* Información del sistema */}
          {settings && (
            <Card>
              <CardTitle className="mb-3">Información del sistema</CardTitle>
              <dl className="flex flex-col gap-2 text-body">
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Proveedor de IA</dt>
                  <dd className="font-mono text-text-primary">
                    {settings.ai_provider}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-text-secondary">
                    Proveedor de transcripción
                  </dt>
                  <dd className="font-mono text-text-primary">
                    {settings.whisper_provider}
                  </dd>
                </div>
              </dl>
              <p className="mt-3 text-small text-text-muted">
                El proveedor de IA y transcripción se configura por variables de
                entorno en el backend.
              </p>
            </Card>
          )}
        </div>
      </main>
    </>
  );
}
