'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  OctagonX,
  Phone,
  RefreshCw,
  Search,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import { useAgents, useBulkAssign, useBulkDelete, useCalls } from '@/lib/queries';
import { getErrorMessage } from '@/lib/api';
import { Header } from '@/components/layout/header';
import { Card } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ScoreBadge, StatusBadge } from '@/components/ui/badge';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/feedback';
import { callAgentName, formatDate, formatDuration } from '@/lib/utils';

/**
 * Resalta la primera aparición de `q` dentro del fragmento devuelto por la
 * búsqueda: es lo que explica por qué salió cada llamada.
 */
function Highlight({ text, q }: { text: string; q: string }) {
  const pos = text.toLowerCase().indexOf(q.toLowerCase());
  if (!q || pos < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, pos)}
      <mark className="rounded-[2px] bg-gold-soft px-0.5 text-text-primary">
        {text.slice(pos, pos + q.length)}
      </mark>
      {text.slice(pos + q.length)}
    </>
  );
}

/** Listado paginado de llamadas con filtros (ejecutivo, estado, fecha, texto y críticos). */
export default function CallsPage() {
  const router = useRouter();
  const [agentId, setAgentId] = useState('');
  const [status, setStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [soloCriticas, setSoloCriticas] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);

  // La búsqueda espera a que se deje de teclear: una petición por palabra, no por letra.
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(busqueda.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [busqueda]);

  const { data: agents } = useAgents();
  const { data, isLoading, error, refetch, isFetching } = useCalls({
    agent_id: agentId ? Number(agentId) : undefined,
    status: status || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    q: q || undefined,
    critical: soloCriticas || undefined,
    page,
    page_size: 20,
  });

  // Selección múltiple: sin esto, asignar veinte llamadas son veinte pantallas.
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set());
  const [accionMsg, setAccionMsg] = useState<string | null>(null);
  const bulkAssign = useBulkAssign();
  const bulkDelete = useBulkDelete();

  const visibles = data?.items ?? [];
  const todasSeleccionadas =
    visibles.length > 0 && visibles.every((c) => seleccion.has(c.id));

  function alternar(id: number) {
    setSeleccion((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      return s;
    });
  }

  function alternarTodas() {
    setSeleccion(todasSeleccionadas ? new Set() : new Set(visibles.map((c) => c.id)));
  }

  async function asignarSeleccion(agentId: number) {
    const r = await bulkAssign.mutateAsync({
      call_ids: [...seleccion],
      agent_id: agentId,
    });
    setAccionMsg(`${r.affected} llamada(s) asignadas.`);
    setSeleccion(new Set());
  }

  async function borrarSeleccion() {
    const r = await bulkDelete.mutateAsync([...seleccion]);
    setAccionMsg(`${r.affected} llamada(s) eliminadas.`);
    setSeleccion(new Set());
  }

  function resetPage<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setPage(1);
    };
  }

  return (
    <>
      <Header title="Llamadas" />
      <main className="flex-1 overflow-y-auto p-6">
        {/* Filtros */}
        <div className="mb-5 flex flex-wrap items-end gap-3">
          <div className="w-64">
            <label
              htmlFor="buscar-llamadas"
              className="mb-1.5 block text-small text-text-secondary"
            >
              Buscar en lo que se dijo
            </label>
            <div className="relative">
              <Search
                size={16}
                aria-hidden
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
              />
              <Input
                id="buscar-llamadas"
                type="search"
                placeholder="p. ej. cancelar, TEA, reclamo"
                value={busqueda}
                maxLength={100}
                onChange={(e) => setBusqueda(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
          <div className="w-48">
            <label className="mb-1.5 block text-small text-text-secondary">
              Ejecutivo
            </label>
            <Select
              value={agentId}
              onChange={(e) => resetPage(setAgentId)(e.target.value)}
            >
              <option value="">Todos</option>
              {agents?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="w-44">
            <label className="mb-1.5 block text-small text-text-secondary">
              Estado
            </label>
            <Select
              value={status}
              onChange={(e) => resetPage(setStatus)(e.target.value)}
            >
              <option value="">Todos</option>
              <option value="QUEUED">En cola</option>
              <option value="TRANSCRIBING">Transcribiendo</option>
              <option value="ANALYZING">Analizando</option>
              <option value="DONE">Listo</option>
              <option value="ERROR">Error</option>
            </Select>
          </div>
          <div className="w-40">
            <label className="mb-1.5 block text-small text-text-secondary">
              Desde
            </label>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => resetPage(setDateFrom)(e.target.value)}
            />
          </div>
          <div className="w-40">
            <label className="mb-1.5 block text-small text-text-secondary">
              Hasta
            </label>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => resetPage(setDateTo)(e.target.value)}
            />
          </div>
          <label className="flex h-10 items-center gap-2 text-small text-text-secondary">
            <input
              type="checkbox"
              checked={soloCriticas}
              onChange={(e) => resetPage(setSoloCriticas)(e.target.checked)}
              className="accent-[var(--rust)]"
            />
            Solo suspendidas por criterio crítico
          </label>
          {(dateFrom || dateTo || agentId || status || busqueda || soloCriticas) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setAgentId('');
                setStatus('');
                setDateFrom('');
                setDateTo('');
                setBusqueda('');
                setSoloCriticas(false);
                setPage(1);
              }}
            >
              Limpiar filtros
            </Button>
          )}
          <div className="ml-auto flex items-center gap-3">
            <Button
              variant="secondary"
              onClick={() => refetch()}
              disabled={isFetching}
              title="Actualizar estado de las llamadas"
            >
              <RefreshCw
                size={18}
                className={isFetching ? 'animate-spin' : undefined}
              />
              Actualizar
            </Button>
            <Link href="/calls/new">
              <Button>
                <UploadCloud size={18} />
                Subir llamadas
              </Button>
            </Link>
          </div>
        </div>

        {isLoading && (
          <div className="flex flex-col gap-2">
            {[0, 1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        )}

        {error && <ErrorState message={getErrorMessage(error)} />}

        {data && data.items.length === 0 && (
          <EmptyState
            icon={<Phone size={48} />}
            title="No hay llamadas"
            description={
              q
                ? `Ninguna transcripción contiene «${q}».`
                : 'No se encontraron llamadas con los filtros seleccionados.'
            }
          />
        )}

        {seleccion.size > 0 && (
          <Card className="mb-4 flex flex-wrap items-center gap-3 !py-3">
            <span className="text-body font-semibold text-text-primary">
              {seleccion.size} seleccionada{seleccion.size > 1 ? 's' : ''}
            </span>
            <Select
              aria-label="Asignar las llamadas seleccionadas a un ejecutivo"
              className="w-auto min-w-[190px]"
              value=""
              onChange={(e) => {
                if (e.target.value) asignarSeleccion(Number(e.target.value));
              }}
            >
              <option value="">Asignar a un ejecutivo…</option>
              {agents?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </Select>
            <Button
              variant="danger"
              size="sm"
              onClick={borrarSeleccion}
              disabled={bulkDelete.isPending}
            >
              <Trash2 size={16} />
              Eliminar
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setSeleccion(new Set())}>
              <X size={16} />
              Quitar selección
            </Button>
          </Card>
        )}

        {accionMsg && (
          <p className="mb-4 text-small text-success">{accionMsg}</p>
        )}

        {data && data.items.length > 0 && (
          <Card className="overflow-hidden !p-0">
            <table className="w-full text-body">
              <thead>
                <tr className="border-b border-border bg-bg-accent/40 text-left">
                  <th className="w-10 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={todasSeleccionadas}
                      onChange={alternarTodas}
                      aria-label="Seleccionar todas las llamadas de la página"
                      className="accent-[var(--rust)]"
                    />
                  </th>
                  <th className="px-4 py-3 text-small text-text-secondary">
                    Ejecutivo
                  </th>
                  <th className="px-4 py-3 text-small text-text-secondary">
                    Subida
                  </th>
                  <th className="px-4 py-3 text-small text-text-secondary">
                    Duración
                  </th>
                  <th className="px-4 py-3 text-small text-text-secondary">
                    Estado
                  </th>
                  <th className="px-4 py-3 text-small text-text-secondary">
                    Score
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((call) => (
                  <tr
                    key={call.id}
                    onClick={() => router.push(`/calls/${call.id}`)}
                    className="cursor-pointer border-b border-border
                               transition-colors last:border-0 hover:bg-bg-accent/30"
                  >
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={seleccion.has(call.id)}
                        onChange={() => alternar(call.id)}
                        aria-label={`Seleccionar la llamada ${call.id}`}
                        className="accent-[var(--rust)]"
                      />
                    </td>
                    <td className="px-4 py-3 text-text-primary">
                      <span className="flex items-center gap-2">
                        {callAgentName(call)}
                        {!call.agent && call.detected_agent_name && (
                          <span
                            className="rounded-control bg-warning/15 px-1.5 py-0.5
                                       text-small font-medium text-warning"
                          >
                            Sin registrar
                          </span>
                        )}
                      </span>
                      {call.match_snippet && q && (
                        <span className="mt-1 block max-w-xl text-small text-text-secondary">
                          <Highlight text={call.match_snippet} q={q} />
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-text-secondary">
                      {formatDate(call.created_at)}
                    </td>
                    <td className="px-4 py-3 font-mono text-text-secondary">
                      {formatDuration(call.duration_seconds)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={call.status} />
                    </td>
                    <td className="px-4 py-3">
                      {call.critical_failed ? (
                        <span
                          className="inline-flex items-center gap-1 rounded-control bg-danger/15
                                     px-2 py-0.5 text-small font-medium text-danger"
                          title="Suspendida por un criterio crítico: nota 0"
                        >
                          <OctagonX size={14} aria-hidden />
                          Suspendida
                        </span>
                      ) : call.global_score != null ? (
                        <ScoreBadge score={call.global_score} />
                      ) : (
                        <span className="text-text-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}

        {/* Paginación */}
        {data && data.total_pages > 1 && (
          <div className="mt-4 flex items-center justify-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Anterior
            </Button>
            <span className="text-small text-text-secondary">
              Página {data.page} de {data.total_pages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        )}
      </main>
    </>
  );
}
