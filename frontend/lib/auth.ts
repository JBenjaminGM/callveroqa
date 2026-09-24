'use client';

import { useEffect, useState } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

/**
 * Estado de autenticación, persistido en localStorage.
 *
 * Guarda el token JWT y el usuario para mantener la sesión entre recargas.
 */
interface AuthState {
  token: string | null;
  user: User | null;
  setSession: (token: string, user: User) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setSession: (token, user) => set({ token, user }),
      clearSession: () => set({ token: null, user: null }),
    }),
    // Renombrada con la marca (antes `callqa-auth`). El coste asumido: los
    // usuarios con un token guardado de la versión anterior vuelven al login.
    { name: 'callveroqa-auth' },
  ),
);

/**
 * True cuando el estado persistido ya se leyó de localStorage.
 *
 * En el primer render `token` siempre es null, porque `persist` rehidrata después
 * de montar. Sin esperar a que termine, cualquier comprobación de sesión concluye
 * que no hay sesión y expulsa al usuario al login en cada recarga de página.
 */
export function useAuthHydrated(): boolean {
  // Arranca en false y solo se consulta `persist` dentro del efecto: durante el
  // prerender en servidor la API de persistencia no existe, y leerla ahí rompe
  // el build.
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const { persist: persistApi } = useAuthStore;
    if (!persistApi) {
      setHydrated(true);
      return;
    }
    if (persistApi.hasHydrated()) setHydrated(true);
    // Y si aún no había terminado, avisa cuando lo haga.
    return persistApi.onFinishHydration(() => setHydrated(true));
  }, []);

  return hydrated;
}

/** Devuelve el token actual leyendo directamente del store (uso fuera de React). */
export function getToken(): string | null {
  return useAuthStore.getState().token;
}

/** True si el usuario tiene permisos de gestión/analítica global (admin o jefe). */
export function isManager(user: User | null | undefined): boolean {
  return !!user && (user.role === 'admin' || user.role === 'jefe');
}
