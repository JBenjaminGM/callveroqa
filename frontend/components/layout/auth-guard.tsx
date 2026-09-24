'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { isManager, useAuthHydrated, useAuthStore } from '@/lib/auth';
import { Spinner } from '@/components/ui/feedback';

// Rutas reservadas a roles de gestión (admin / jefe). El asesor que intente
// entrar se redirige a su panel personal.
const MANAGER_ONLY = [
  '/dashboard',
  '/agents',
  '/campaigns',
  '/settings',
  '/calls/new',
  '/calibracion',
  '/usuarios',
];

function isManagerOnly(path: string): boolean {
  return MANAGER_ONLY.some((p) => path === p || path.startsWith(p + '/'));
}

/**
 * Protege las páginas autenticadas y enruta según el rol.
 *
 * - Sin token → login.
 * - Asesor en una ruta de gestión → su panel personal (/mi-panel).
 * - Manager en /mi-panel → dashboard.
 *
 * Espera a que `persist` haya rehidratado el store antes de decidir: si no, en
 * cada recarga el token aún es null y expulsaría al usuario al login.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const hydrated = useAuthHydrated();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace('/login');
      return;
    }
    const manager = isManager(user);
    if (!manager && isManagerOnly(pathname)) {
      router.replace('/mi-panel');
      return;
    }
    if (manager && pathname.startsWith('/mi-panel')) {
      router.replace('/dashboard');
      return;
    }
    setReady(true);
  }, [hydrated, token, user, pathname, router]);

  if (!hydrated || !ready) {
    return (
      <div className="flex h-screen items-center justify-center text-accent-primary">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return <>{children}</>;
}
