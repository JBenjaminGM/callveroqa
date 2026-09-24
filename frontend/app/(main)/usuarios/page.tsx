'use client';

import { useState } from 'react';
import { KeyRound, ShieldCheck, UserPlus, Users2 } from 'lucide-react';
import {
  useAgents,
  useCreateUser,
  useResetUserPassword,
  useUpdateUser,
  useUsers,
} from '@/lib/queries';
import { getErrorMessage } from '@/lib/api';
import { useAuthStore } from '@/lib/auth';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { ErrorState, Skeleton, Spinner } from '@/components/ui/feedback';
import { formatDateTime } from '@/lib/utils';
import type { AccountUser } from '@/types';

const ROLES = [
  { value: 'admin', label: 'Administrador' },
  { value: 'jefe', label: 'Jefe de área' },
  { value: 'asesor', label: 'Asesor' },
];

function roleLabel(role: string) {
  return ROLES.find((r) => r.value === role)?.label ?? role;
}

/**
 * Altas, bajas y contraseñas del equipo.
 *
 * Las contraseñas **se enseñan una sola vez**: aquí se generan al crear una
 * cuenta o al resetearla, y no hay forma de volver a leerlas. Por eso la
 * pantalla las muestra en un aviso persistente hasta que se cierra, en vez de
 * en un mensaje que se desvanece solo.
 */
export default function UsuariosPage() {
  const yo = useAuthStore((s) => s.user);
  const { data: usuarios, isLoading, error } = useUsers();
  const { data: agents } = useAgents({ active: true });
  const crear = useCreateUser();
  const actualizar = useUpdateUser();
  const resetear = useResetUserPassword();

  const [form, setForm] = useState({ name: '', email: '', role: 'jefe', agent_id: '' });
  const [aviso, setAviso] = useState<{ email: string; password: string } | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);

  async function onCrear(e: React.FormEvent) {
    e.preventDefault();
    setFallo(null);
    try {
      const creado = await crear.mutateAsync({
        name: form.name,
        email: form.email,
        role: form.role,
        agent_id: form.role === 'asesor' && form.agent_id ? Number(form.agent_id) : undefined,
      });
      if (creado.generated_password) {
        setAviso({ email: creado.user.email, password: creado.generated_password });
      }
      setForm({ name: '', email: '', role: 'jefe', agent_id: '' });
      setAbierto(false);
    } catch (err) {
      setFallo(getErrorMessage(err));
    }
  }

  async function onResetear(u: AccountUser) {
    if (!confirm(`¿Generar una contraseña nueva para ${u.email}? La actual dejará de servir.`)) {
      return;
    }
    setFallo(null);
    try {
      const password = await resetear.mutateAsync(u.id);
      setAviso({ email: u.email, password });
    } catch (err) {
      setFallo(getErrorMessage(err));
    }
  }

  async function onCambiar(u: AccountUser, cambios: Partial<AccountUser>) {
    setFallo(null);
    try {
      await actualizar.mutateAsync({ id: u.id, ...cambios });
    } catch (err) {
      setFallo(getErrorMessage(err));
    }
  }

  return (
    <>
      <Header title="Usuarios" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <p className="text-body text-text-secondary">
            Quién entra a la plataforma y con qué permisos
          </p>
          <Button onClick={() => setAbierto((v) => !v)}>
            <UserPlus size={18} />
            Nueva cuenta
          </Button>
        </div>

        {/* La contraseña solo se puede leer aquí y ahora. */}
        {aviso && (
          <Card className="mb-4 border-gold/40 bg-gold-soft/40">
            <CardTitle className="mb-1 flex items-center gap-2">
              <KeyRound size={18} />
              Contraseña de {aviso.email}
            </CardTitle>
            <p className="mb-2 text-small text-text-secondary">
              Cópiala y entrégasela ahora: no se puede volver a consultar. Quien la
              reciba puede cambiarla desde «Mi cuenta».
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <code className="rounded-control bg-bg-card px-3 py-1.5 font-mono text-body text-text-primary">
                {aviso.password}
              </code>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigator.clipboard?.writeText(aviso.password)}
              >
                Copiar
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setAviso(null)}>
                Ya la guardé
              </Button>
            </div>
          </Card>
        )}

        {fallo && <div className="mb-4"><ErrorState message={fallo} /></div>}

        {abierto && (
          <Card className="mb-4">
            <CardTitle className="mb-3">Nueva cuenta</CardTitle>
            <form onSubmit={onCrear} className="flex flex-wrap items-end gap-3">
              <div className="w-56">
                <label className="mb-1.5 block text-small text-text-secondary">Nombre</label>
                <Input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Nombre y apellidos"
                />
              </div>
              <div className="w-64">
                <label className="mb-1.5 block text-small text-text-secondary">Email</label>
                <Input
                  required
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="persona@banco.com"
                />
              </div>
              <div className="w-44">
                <label className="mb-1.5 block text-small text-text-secondary">Rol</label>
                <Select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </Select>
              </div>
              {form.role === 'asesor' && (
                <div className="w-56">
                  <label className="mb-1.5 block text-small text-text-secondary">
                    Ejecutivo evaluado
                  </label>
                  <Select
                    required
                    value={form.agent_id}
                    onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
                  >
                    <option value="">Selecciona…</option>
                    {agents?.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                  </Select>
                </div>
              )}
              <Button type="submit" disabled={crear.isPending}>
                {crear.isPending ? <Spinner /> : <UserPlus size={16} />}
                Crear y generar contraseña
              </Button>
              <Button type="button" variant="ghost" onClick={() => setAbierto(false)}>
                Cancelar
              </Button>
            </form>
          </Card>
        )}

        {isLoading && <Skeleton className="h-64" />}
        {error && <ErrorState message={getErrorMessage(error)} />}

        {usuarios && (
          <Card className="overflow-hidden !p-0">
            <table className="w-full text-body">
              <thead>
                <tr className="border-b border-border bg-bg-accent/40 text-left">
                  <th className="px-4 py-3 text-small text-text-secondary">Persona</th>
                  <th className="px-4 py-3 text-small text-text-secondary">Rol</th>
                  <th className="px-4 py-3 text-small text-text-secondary">Último acceso</th>
                  <th className="px-4 py-3 text-small text-text-secondary">Estado</th>
                  <th className="px-4 py-3 text-small text-text-secondary">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => {
                  const soyYo = u.id === yo?.id;
                  return (
                    <tr
                      key={u.id}
                      className="border-b border-border last:border-0"
                    >
                      <td className="px-4 py-3">
                        <span className="flex items-center gap-2 text-text-primary">
                          {u.name}
                          {soyYo && (
                            <span className="rounded-control bg-bg-accent px-1.5 py-0.5 text-small text-text-muted">
                              tú
                            </span>
                          )}
                          {u.is_readonly && (
                            <span className="inline-flex items-center gap-1 rounded-control bg-gold-soft px-1.5 py-0.5 text-small text-text-secondary">
                              <ShieldCheck size={12} aria-hidden />
                              demo
                            </span>
                          )}
                        </span>
                        <span className="block text-small text-text-muted">{u.email}</span>
                      </td>
                      <td className="px-4 py-3">
                        {u.is_readonly || soyYo ? (
                          <span className="text-text-secondary">{roleLabel(u.role)}</span>
                        ) : (
                          <Select
                            aria-label={`Rol de ${u.name}`}
                            className="w-40 !py-1.5 text-small"
                            value={u.role}
                            onChange={(e) => onCambiar(u, { role: e.target.value })}
                          >
                            {ROLES.map((r) => (
                              <option key={r.value} value={r.value}>
                                {r.label}
                              </option>
                            ))}
                          </Select>
                        )}
                      </td>
                      <td className="px-4 py-3 text-small text-text-secondary">
                        {u.last_login ? formatDateTime(u.last_login) : 'Nunca'}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            u.active
                              ? 'rounded-control bg-success/15 px-2 py-0.5 text-small font-medium text-success'
                              : 'rounded-control bg-bg-accent px-2 py-0.5 text-small font-medium text-text-muted'
                          }
                        >
                          {u.active ? 'Activa' : 'Desactivada'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={u.is_readonly || resetear.isPending}
                            onClick={() => onResetear(u)}
                            title="Generar una contraseña nueva"
                          >
                            <KeyRound size={14} />
                            Resetear
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={u.is_readonly || soyYo}
                            onClick={() => onCambiar(u, { active: !u.active })}
                            title={
                              soyYo
                                ? 'No puedes desactivar tu propia cuenta'
                                : u.active
                                  ? 'Cerrar el acceso sin borrar el historial'
                                  : 'Devolver el acceso'
                            }
                          >
                            {u.active ? 'Desactivar' : 'Activar'}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )}

        <p className="mt-4 flex items-center gap-2 text-small text-text-muted">
          <Users2 size={14} aria-hidden />
          Desactivar no borra: las llamadas y revisiones de esa persona siguen
          contando en el histórico del equipo.
        </p>
      </main>
    </>
  );
}
