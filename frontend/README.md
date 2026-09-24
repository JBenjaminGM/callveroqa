# 🎨 CallVeroQA — Frontend

Interfaz web de la plataforma de Quality Assurance automatizado para call centers
del sector banca. Construida con **Next.js 14**, TypeScript y
Tailwind CSS.

> ⚠️ **No utilizar con datos reales de clientes sin la aprobación previa de
> Compliance.** (El banner visible de "vista previa" se retiró de la UI.)

---

## 1. ¿Qué es esto?

La aplicación que usan los distintos roles de QA. La navegación y la redirección
se adaptan al rol:

- **admin / jefe** (mismos permisos): suben y siguen llamadas, ven el dashboard
  global y los perfiles de ejecutivos, gestionan el equipo, las campañas, la
  rúbrica y los umbrales QA. Redirigen a `/dashboard`.
- **asesor:** solo ve su ficha, sus llamadas y su panel **"Mi rendimiento"**
  (`/mi-panel`); recibe los demás accesos bloqueados por guard de rol.

Se conecta al backend de CallVeroQA mediante su API REST.

---

## 2. Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework | Next.js 14 (App Router) |
| Lenguaje | TypeScript |
| Estilos | Tailwind CSS + variables CSS (modo claro/oscuro) |
| Datos del servidor | TanStack Query + Axios |
| Estado de sesión | Zustand (persistido en localStorage) |
| Formularios | React Hook Form + Zod |
| Gráficos | Recharts |
| Tipografía | Manrope · Inter · IBM Plex Mono (`next/font/google`) |
| Iconos | lucide-react |

---

## 3. Requisitos previos

- **Node.js 18 o superior** — https://nodejs.org
- El **backend de CallVeroQA** corriendo (local con Docker, o desplegado en Render).

---

## 4. Configuración local (paso a paso)

```bash
# 1. Sitúate en la carpeta del proyecto
cd callveroqa/frontend

# 2. Copia el archivo de variables de entorno
#    En Windows (PowerShell):  Copy-Item .env.local.example .env.local
cp .env.local.example .env.local

# 3. Edita .env.local con la URL de tu backend
#    NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# 4. Instala dependencias
npm install

# 5. Arranca el servidor de desarrollo
npm run dev
```

Abre **http://localhost:3000**.

### Cuentas sembradas

| Rol | Email |
|---|---|
| admin | `admin@callveroqa.com` |
| jefe | `jefe@callveroqa.com` |
| asesor | el email del ejecutivo (p. ej. `maria@banco.com`) |

> **Las contraseñas se generan al azar en el primer *seed* y se imprimen una sola
> vez.** Léelas con `docker compose logs api`, o fíjalas tú definiendo
> `SEED_ADMIN_PASSWORD`, `SEED_JEFE_PASSWORD` y `SEED_ASESOR_PASSWORD` antes de
> sembrar. Si una cuenta todavía usa una de las contraseñas que llegaron a estar
> publicadas en el repositorio, el *seed* la rota automáticamente.

---

## 5. Desplegar en Vercel

El despliegue vigente es **Vercel** (frontend) + **Render** (backend), gratis ($0).
Guía completa: [`../docs/DEPLOY_GRATIS.md`](../docs/DEPLOY_GRATIS.md). En vivo:
https://callveroqa.vercel.app (API: https://callveroqa-api.onrender.com).

1. Sube el repositorio a GitHub.
2. Entra a https://vercel.com/new e importa el repositorio.
3. **Root Directory:** selecciona `frontend/`. Vercel detecta que es Next.js.
4. En **Environment Variables** añade la URL de tu backend en Render:

   ```
   NEXT_PUBLIC_API_URL=https://callveroqa-api.onrender.com/api/v1
   ```

5. Pulsa **Deploy**. En ~2 minutos tendrás una URL pública.
6. **Importante:** en el backend (Render), añade la URL de Vercel a la
   variable `CORS_ORIGINS` para que la API acepte las peticiones del frontend.

> Cold-start del plan gratis de Render: el cliente (`lib/api.ts`) tolera el
> arranque en frío del backend (timeout 90 s, reintentos y mensaje "activando el
> servidor"). Detalles en `../docs/DEPLOY_GRATIS.md`.

---

## 6. Estructura del proyecto

```
frontend/
├── app/
│   ├── layout.tsx          # Layout raíz: fuentes (next/font/google), tema, providers
│   ├── providers.tsx       # TanStack Query
│   ├── page.tsx            # Redirección inicial (por rol)
│   ├── login/page.tsx      # Inicio de sesión
│   └── (main)/             # Páginas autenticadas (sidebar + header)
│       ├── layout.tsx
│       ├── dashboard/      # KPIs del equipo (admin/jefe)
│       ├── mi-panel/       # "Mi rendimiento" (asesor)
│       ├── calls/          # Listado, subida y detalle de llamadas
│       ├── agents/         # Listado y perfil de ejecutivos
│       ├── campaigns/      # Campañas: lista, crear (PDF/IA/formulario), editar
│       └── settings/       # Rúbrica, idioma y umbrales QA
├── components/
│   ├── ui/                 # Primitivos (Button, Card, Input, Badge, Section…)
│   ├── layout/             # Sidebar, Header, toggle de tema
│   ├── dashboard/          # viz (gauge/sparkline/donut), StatCard, insights, trend-chart
│   └── charts/             # ScoreRadar
├── lib/
│   ├── api.ts              # Cliente Axios + interceptores + resiliencia cold-start
│   ├── auth.ts             # Store de sesión (Zustand) + rol
│   ├── queries.ts          # Hooks de TanStack Query
│   └── utils.ts            # Helpers (formato, scores, clases)
├── public/
│   └── favicon.svg         # Ícono waveform de la marca
├── types/index.ts          # Tipos que reflejan la API
└── tailwind.config.ts      # Sistema de diseño
```

---

## 7. Sistema de diseño — identidad CallVeroQA

La fuente de verdad de la marca es **[`docs/BRAND.md`](../docs/BRAND.md)**. La
implementación canónica del color son las variables CSS de `app/globals.css`,
mapeadas a Tailwind en `tailwind.config.ts`.

- **Paleta:** paper (#F5F1E8) e ink (#2A2420) dominan; **rust** (#B8441F) es el
  acento de marca y **gold** (#A67C27) el secundario.
- **Modo claro por defecto** + modo oscuro derivado; el toggle del header
  persiste la elección en `localStorage`.
- **Sidebar** siempre en ink, con el wordmark en negativo y el "Vero" en rust.
- **Tipografía:** Manrope en titulares, Inter en cuerpo y UI, IBM Plex Mono
  **solo** para datos numéricos (scores, IDs, marcas de tiempo).
- **Radios:** 8px en contenedores (`rounded-card`), 6px en controles
  (`rounded-control`). Sombras sutiles, sin glassmorphism ni gradientes.
- Scores con color semántico: verde (80-100), ámbar (60-79), rojo (0-59).

> Las identidades visuales anteriores están **obsoletas**; se describen en
> `docs/HISTORIA.md`.

---

## 8. Solución de problemas comunes

| Problema | Solución |
|---|---|
| Error de CORS en consola | Añade la URL del frontend a `CORS_ORIGINS` en el backend. |
| "Network Error" al iniciar sesión | Verifica que el backend esté corriendo y que `NEXT_PUBLIC_API_URL` sea correcta. En Render puede ser un cold-start: espera ~50 s al primer acceso. |
| La sesión se pierde al recargar | Revisa que el navegador permita `localStorage`. |
| Los estilos no cargan | Borra `.next/` y vuelve a ejecutar `npm run dev`. |
