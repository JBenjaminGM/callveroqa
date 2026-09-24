'use client';

import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { useChangePassword } from '@/lib/queries';
import { getErrorMessage } from '@/lib/api';
import { useAuthStore } from '@/lib/auth';
import { Header } from '@/components/layout/header';
import { Card, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ErrorState, Spinner } from '@/components/ui/feedback';
import { formatDateTime } from '@/lib/utils';

const MIN_LONGITUD = 10;

const ROLES: Record<string, string> = {
  admin: 'Administrador',
  jefe: 'Jefe de área',
  asesor: 'Asesor',
};

/**
 * Mi cuenta: lo único que puede hacer aquí cualquiera es cambiar su contraseña.
 *
 * Existe porque las contraseñas se entregan generadas y hasta ahora nadie podía
 * cambiar la suya sin tocar la base de datos, que es inaceptable en un banco.
 */
export default function MiCuentaPage() {
  const user = useAuthStore((s) => s.user);
  const cambiar = useChangePassword();
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [ok, setOk] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  const noCoincide = repetida.length > 0 && nueva !== repetida;
  const corta = nueva.length > 0 && nueva.length < MIN_LONGITUD;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFallo(null);
    setOk(false);
    if (nueva !== repetida) {
      setFallo('La contraseña nueva y su repetición no coinciden.');
      return;
    }
    try {
      await cambiar.mutateAsync({ current_password: actual, new_password: nueva });
      setOk(true);
      setActual('');
      setNueva('');
      setRepetida('');
    } catch (err) {
      setFallo(getErrorMessage(err));
    }
  }

  return (
    <>
      <Header title="Mi cuenta" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="flex max-w-xl flex-col gap-4">
          <Card>
            <CardTitle className="mb-3">Tus datos</CardTitle>
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-body">
              <dt className="text-text-secondary">Nombre</dt>
              <dd className="text-text-primary">{user?.name ?? '—'}</dd>
              <dt className="text-text-secondary">Email</dt>
              <dd className="text-text-primary">{user?.email ?? '—'}</dd>
              <dt className="text-text-secondary">Rol</dt>
              <dd className="text-text-primary">
                {ROLES[user?.role ?? ''] ?? user?.role ?? '—'}
              </dd>
              <dt className="text-text-secondary">Último acceso</dt>
              <dd className="text-text-primary">
                {user?.last_login ? formatDateTime(user.last_login) : '—'}
              </dd>
            </dl>
            <p className="mt-3 text-small text-text-muted">
              Para cambiar tu nombre o tu rol, habla con un administrador.
            </p>
          </Card>

          <Card>
            <CardTitle className="mb-1 flex items-center gap-2">
              <KeyRound size={18} />
              Cambiar contraseña
            </CardTitle>
            <p className="mb-4 text-small text-text-secondary">
              Mínimo {MIN_LONGITUD} caracteres. Si te entregaron una contraseña
              generada, cámbiala en cuanto entres.
            </p>

            <form onSubmit={onSubmit} className="flex flex-col gap-3">
              <div>
                <label
                  htmlFor="actual"
                  className="mb-1.5 block text-small text-text-secondary"
                >
                  Contraseña actual
                </label>
                <Input
                  id="actual"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={actual}
                  onChange={(e) => setActual(e.target.value)}
                />
              </div>
              <div>
                <label
                  htmlFor="nueva"
                  className="mb-1.5 block text-small text-text-secondary"
                >
                  Contraseña nueva
                </label>
                <Input
                  id="nueva"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={nueva}
                  onChange={(e) => setNueva(e.target.value)}
                />
                {corta && (
                  <p className="mt-1 text-small text-danger">
                    Le faltan {MIN_LONGITUD - nueva.length} caracteres.
                  </p>
                )}
              </div>
              <div>
                <label
                  htmlFor="repetida"
                  className="mb-1.5 block text-small text-text-secondary"
                >
                  Repite la contraseña nueva
                </label>
                <Input
                  id="repetida"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={repetida}
                  onChange={(e) => setRepetida(e.target.value)}
                />
                {noCoincide && (
                  <p className="mt-1 text-small text-danger">No coinciden.</p>
                )}
              </div>

              {fallo && <ErrorState message={fallo} />}
              {ok && (
                <p className="text-small text-success">
                  Contraseña cambiada. Úsala la próxima vez que entres.
                </p>
              )}

              <div>
                <Button
                  type="submit"
                  disabled={cambiar.isPending || noCoincide || corta || !actual}
                >
                  {cambiar.isPending ? <Spinner /> : <KeyRound size={16} />}
                  Cambiar contraseña
                </Button>
              </div>
            </form>
          </Card>
        </div>
      </main>
    </>
  );
}
