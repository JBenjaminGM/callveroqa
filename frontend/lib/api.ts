'use client';

import axios, { AxiosError, type AxiosRequestConfig } from 'axios';
import { getToken, useAuthStore } from '@/lib/auth';

/**
 * Instancia de Axios configurada para hablar con el backend de CallVeroQA.
 *
 * - Añade automáticamente el token JWT en cada petición.
 * - Reintenta ante un "cold start" del backend (Render plan gratis se duerme y
 *   tarda en arrancar; durante ese arranque responde 502/503/504 o no responde).
 * - Si el backend responde 401, limpia la sesión y redirige al login.
 */
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1',
  // Margen amplio para tolerar el arranque en frío del backend (~50s).
  timeout: 90000,
});

// Interceptor de petición: añade la cabecera Authorization.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const COLD_START_CODES = [502, 503, 504];
const MAX_RETRIES = 2;

// Interceptor de respuesta: reintenta el cold start y gestiona el 401.
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as
      | (AxiosRequestConfig & { _retryCount?: number })
      | undefined;
    const status = error.response?.status;

    // Cold start / backend despertando: reintenta con una pequeña espera.
    const isColdStart = !error.response || COLD_START_CODES.includes(status ?? 0);
    if (config && isColdStart && (config._retryCount ?? 0) < MAX_RETRIES) {
      config._retryCount = (config._retryCount ?? 0) + 1;
      await new Promise((resolve) => setTimeout(resolve, 5000 * config._retryCount!));
      return api(config);
    }

    if (status === 401 && typeof window !== 'undefined') {
      useAuthStore.getState().clearSession();
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

/** Extrae un mensaje de error legible de una excepción de Axios. */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    // Sin respuesta del servidor: cold start o red caída.
    if (!error.response) {
      return 'No se pudo conectar con el servidor. Si acaba de iniciarse, espera unos segundos y reinténtalo.';
    }
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    return error.message;
  }
  return 'Ocurrió un error inesperado.';
}
