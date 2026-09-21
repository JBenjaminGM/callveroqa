# 🧠 Estado del Proyecto — CallVeroQA

> **Memoria de desarrollo.** Este documento resume lo construido, las decisiones y lo pendiente.
>
> 👉 **Para el estado MÁS ACTUAL y la guía de desarrollo** (cómo correr, testear, desplegar y
> dónde tocar cada cosa), ver **[`AGENTS.md`](AGENTS.md)** y **[`CHANGELOG.md`](CHANGELOG.md)**.

**Última actualización:** Septiembre 2026
**Estado general:** ✅ Plataforma funcional. **87 tests** backend en verde. **Fase 2
(analítica de alto impacto)**, **rediseño premium de indicadores** y **rebrand a
CallVeroQA** aplicados.

> ⚠️ **PRODUCCIÓN RECONSTRUIDA (septiembre 2026).** La PostgreSQL del plan gratuito de
> Render **caducó y fue eliminada**, así que el backend llevaba dos meses muriendo al
> arrancar (`could not translate host name "dpg-…"`). **Los datos de producción se
> perdieron** y no había copia de seguridad. Se recreó la infraestructura ya con el
> nombre nuevo: `callaibrate-api` + `callaibrate-db`. Detalle en
> [`RENOMBRADO_INFRA.md`](RENOMBRADO_INFRA.md).
>
> 🔑 **La `GROQ_API_KEY` la pones tú** en Render → `callaibrate-api` → **Environment**
> (es `sync: false`: vive solo ahí, nunca en el repo, y `git push` no la actualiza). La
> clave que se filtró en `aeda304` está **revocada**; la válida está en tu `backend/.env`.
>
> ⏳ El plan gratuito **volverá a caducar la base a los 30 días**. Si esto tiene que
> durar, hay que pasar a plan de pago o programar volcados con `pg_dump`.

---

## 1. ¿Qué es CallVeroQA?

Plataforma web de **Quality Assurance automatizado con IA** para call centers
bancarios. El usuario sube grabaciones de llamadas; la IA las transcribe
(Groq Whisper large v3), **enmascara la PII** (best-effort), identifica al
ejecutivo y las **evalúa** con un LLM (Groq Llama 3.3 70B) contra una rúbrica
dinámica, produciendo scores por dimensión, un score global ponderado,
recomendaciones accionables y un reporte PDF. Sector: banca.

> ⚠️ **No debe usarse con datos reales de clientes sin la aprobación previa de
> Compliance.** Por decisión del responsable, el **banner visible de "vista previa"
> se RETIRÓ de la UI** (la plataforma se presenta como producto acabado). Como
> salvaguarda interna se conservan el header HTTP `X-Prototype-Notice` y el log JSON
> `environment="evaluation"`.

---

## 2. Arquitectura y stack

```
Navegador ──HTTPS──> Frontend (Next.js 14) ──REST──> Backend (FastAPI)
                                                         │
                                  ┌──────────────────────┼───────────────┐
                                  ▼              ▼                ▼
                            PostgreSQL        Redis          Celery worker
                                                              │   │
                                                       Groq ◄─┘   └─► Groq (LLM)
                                                    (Whisper)     (análisis · Claude/GPT opc.)
```

> En Render (producción gratis) **no hay Celery/Redis**: el procesamiento es
> **inline** vía `BackgroundTasks` (`PROCESS_INLINE=true`).

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, slowapi |
| Seguridad / auth | python-jose + passlib (JWT + bcrypt) |
| HTTP / PDF | httpx · reportlab (genera PDF) · pypdf (lee PDF) · boto3 (S3 opcional) |
| Procesamiento asíncrono | Celery 5 + Redis (local) · inline con `BackgroundTasks` (Render) |
| Base de datos | PostgreSQL 15 |
| IA — transcripción | Groq API (Whisper large v3) |
| IA — análisis | Groq (Llama 3.3 70B, gratis) · factory portable a Claude / OpenAI / Azure |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Datos en frontend | TanStack Query + Axios; estado de sesión con Zustand |
| Gráficos | Recharts |
| Tipografía | Manrope · Inter · IBM Plex Mono (`next/font/google`) |
| Contenedores | Docker Compose (todo el stack) |

---

## 3. Estructura del monorepo

```
callqa-ai/
├── docker-compose.yml        # Levanta TODO el stack local: bd + redis + api + worker + frontend
├── render.yaml               # Blueprint de Render (backend Docker + PostgreSQL)
├── README.md                 # Guía rápida del monorepo
├── AGENTS.md / CLAUDE.md      # Punteros que apuntan a docs/AGENTS.md
│
├── .github/workflows/
│   └── keepalive.yml         # Ping a /health cada 12 min (mitiga el cold-start de Render)
│
├── backend/                  # API FastAPI + worker Celery
│   ├── app/
│   │   ├── main.py            # Arranque, CORS, logging JSON, routers
│   │   ├── config.py          # Configuración por variables de entorno
│   │   ├── models/            # Tablas SQLAlchemy
│   │   ├── schemas/           # DTOs Pydantic
│   │   ├── routers/           # Endpoints REST
│   │   ├── services/          # Lógica de negocio (IA, storage, matching, PDF, PDF de campañas)
│   │   ├── tasks/             # Tareas Celery
│   │   └── prompts/           # Prompts para los LLM
│   ├── alembic/               # Migraciones de BD (0001 … 0006)
│   ├── scripts/seed_data.py   # Datos iniciales (no imprime contraseñas)
│   ├── tests/                 # 78 tests automatizados
│   └── docker-compose.yml     # Compose SOLO del backend (para devs)
│
├── frontend/                 # Aplicación Next.js
│   ├── app/                   # Páginas (login + grupo (main) + /campaigns + /mi-panel)
│   │   └── globals.css        # Tokens de color CallVeroQA (implementación canónica)
│   ├── components/            # UI, layout, charts, dashboard
│   ├── lib/
│   │   └── api.ts             # Axios + resiliencia de cold-start (timeout 90s, reintentos)
│   ├── public/favicon.svg     # Ícono waveform de la marca
│   ├── types/                 # Tipos TypeScript
│   ├── tailwind.config.ts     # Mapea los tokens a clases de Tailwind
│   └── Dockerfile             # Imagen de producción (salida standalone)
│
└── docs/                     # TODA la documentación del proyecto
    ├── AGENTS.md              # Guía canónica de desarrollo (la más importante)
    ├── 00_INDICE.md           # Índice de la documentación
    ├── ESTADO_DEL_PROYECTO.md # Este archivo (memoria del proyecto)
    └── CHANGELOG.md · DEPLOY_GRATIS.md
```

---

## 4. Funcionalidades implementadas

### Backend

- **Autenticación** JWT (login, refresh, logout, me) con rate limiting en login
  (5 intentos / 15 min). `me` devuelve `role` y `agent_id`.
- **Roles y scoping**: tres roles — `admin`, `jefe` (mismos permisos por ahora,
  vía helper `is_manager`) y `asesor` (solo ve su propio rendimiento). La
  dependencia `require_manager` protege los endpoints de gestión.
- **Ejecutivos** (agents): alta, edición, baja lógica, estadísticas y
  **creación del login del asesor** (`POST /agents/{id}/login`, vincula User↔Agent).
- **Campañas con nota de producto**: entidad `Campaign` con una nota de producto
  de 9 campos; se crea por formulario (con asistente IA), o subiendo un **PDF**
  que la IA parsea (pypdf + LLM) y autocompleta. La nota se **inyecta en el
  prompt de análisis** para evaluar si el ejecutivo ofreció la oferta correcta.
- **Llamadas**: subida individual y **en lote**, listado paginado con filtros
  (ejecutivo, estado, **rango de fechas**, campaña), detalle, estado para
  polling, asignación, reintento (idempotente), reporte PDF, borrado.
- **Procesamiento** (`QUEUED → TRANSCRIBING → ANALYZING → DONE`): Celery en
  local; **inline** (`BackgroundTasks`) en Render.
- **Dashboard**: KPIs del equipo, distribución de scores, rankings, performance
  por ejecutivo, con filtros (campaña, ejecutivo, fechas, periodo).
- **Configuración**: rúbrica **editable** (dimensiones por defecto, con
  subcategorías activables y posibilidad de añadir/eliminar categorías; la IA
  usa las subcategorías activas), idioma de análisis y **umbrales QA**
  configurables (objetivo, alerta de asesor, llamada roja, mínimo de llamadas
  para ranking, alerta de caída de tendencia).
- **Seguridad**: enmascarado best-effort de datos sensibles (tarjetas, DNI, CVV)
  antes de enviar texto a la IA; contraseñas con bcrypt; CORS por lista blanca.
- **Patrón factory** para proveedores de IA y transcripción → portable a
  Claude / OpenAI / Azure (solo configuración).

### Fase 2 — Analítica de alto impacto

- **Métricas de conversación** deterministas ($0) desde los segmentos de la
  transcripción (`conversation_metrics_service`): talk-to-listen ratio, % de
  silencio/dead-air, monólogo más largo del agente, palabras/min y turnos/min.
  Columna `calls.conversation_metrics` (migración 0006), cálculo en el pipeline y
  **al vuelo** para llamadas antiguas.
- **Compliance de nota de producto** (`compliance_service`): cobertura de frases
  obligatorias y detección de claims prohibidos (best-effort por palabras clave).
- **Endpoints de analítica** (`dashboard_service`): `/dashboard/by-campaign`,
  `/alerts`, `/top-recommendations` (manager) y `/agents/{id}/percentile`,
  `/agents/{id}/recommendations` (scoped). `/summary` extendido con
  `team_dimension_averages`, `avg_duration_seconds`, `red_call_count` y
  `conversation_summary`.

### Frontend

- Login (sin credenciales demo a la vista), dashboard, listado/subida/detalle de
  llamadas, ejecutivos, **campañas** (lista, crear vía PDF/IA/formulario, editar),
  configuración y **Mi rendimiento** (panel del asesor).
- **Navegación y redirección por rol**: asesor → `/mi-panel`; admin/jefe →
  `/dashboard`; guard por rol que devuelve 403 a quien no corresponde.
- Identidad visual **CallVeroQA** (modo claro por defecto, sidebar en ink).
- **Dashboard del jefe (Fase 2)**: toolbar compacto con control segmentado, banda
  de resumen con **gauge de score** + KPI cards con delta/sparkline, tendencias
  (área con gradiente + donut de distribución), **tabla de campañas** con barras y
  deltas, **alertas accionables** por severidad, rankings y dinámica de conversación.
- **Vista asesor (`/mi-panel`)**: percentil anónimo, "qué cambiar" con evidencia,
  desglose por campaña + cumplimiento de la nota de producto.
- **Editor de umbrales QA** en `/settings` y **"crear acceso de asesor"** en `agents/[id]`.
- Polling automático del estado de las llamadas en proceso.
- **Resiliencia de cold-start** en `lib/api.ts` (timeout 90 s, reintentos,
  mensaje "activando el servidor").
- **Sistema de dataviz premium** (`components/dashboard/viz.tsx`): `ScoreGauge`,
  `Sparkline`, `Donut`, `MiniProgress`, `DeltaPill`, `BrandTooltip`, `StatCard`,
  `CallsTrendChart`. Banner de prototipo retirado de la UI.

---

## 5. Flujo de trabajo (versión actual)

1. Un manager (admin/jefe) sube **un grupo de audios MP3**. Solo indica: los
   archivos, la **campaña**, un **comentario opcional** y el **responsable** de
   la subida. No elige ejecutivo.
2. Por cada llamada, la IA transcribe el audio, **enmascara la PII** y **detecta
   el nombre del ejecutivo** (siempre se presenta al inicio de la llamada).
3. El nombre detectado se compara (**matching difuso**, tolera erratas como
   "Juan Perz" → "Juan Pérez") con los ejecutivos registrados:
   - **Coincide** → la llamada se asigna a ese ejecutivo.
   - **No coincide** → la llamada queda con el nombre detectado y la etiqueta
     "Sin registrar".
4. La IA **evalúa** la llamada contra la rúbrica dinámica, inyectando la **nota
   de producto** de la campaña para comprobar si se ofreció la oferta correcta.
5. El manager puede **crear** después al ejecutivo no registrado; al crearlo, sus
   llamadas previas se le **vinculan automáticamente**. También puede asignar
   manualmente desde el detalle de cada llamada.
6. El manager consulta el **dashboard** y el detalle individual de cada
   llamada/ejecutivo. El **asesor** entra a su panel **"Mi rendimiento"** y solo
   ve su ficha y sus propias llamadas.

---

## 6. Sistema de diseño

Identidad **CallVeroQA**. La fuente de verdad de la marca es
**[`BRAND.md`](BRAND.md)**; **[`DESIGN.md`](DESIGN.md)** explica cómo se implementa.

- Paleta: **paper `#F5F1E8`** e **ink `#2A2420`** dominan; **rust `#B8441F`** es el
  acento de marca y **gold `#A67C27`** el secundario. `success`/`danger` son
  funcionales, no decorativos.
- **Modo claro por defecto** + **modo oscuro derivado** (addendum de `BRAND.md`).
- **Sidebar siempre en ink**, con el wordmark en negativo y el "Vero" en rust.
- Radios de **8px** en contenedores y **6px** en controles; sombras sutiles, sin
  glassmorphism ni gradientes decorativos.
- Titulares en **caso frase** con una palabra clave opcional en rust (`.hl`).
- Tipografías **Manrope / Inter / IBM Plex Mono** (esta última solo para datos
  numéricos), cargadas con `next/font/google`.
- **Implementación canónica del color:** `frontend/app/globals.css` + `tailwind.config.ts`.

> Nota histórica: hubo tres identidades visuales antes de esta y **todas quedaron
> obsoletas** al adoptar la de CallVeroQA. Se describen en
> [`HISTORIA.md`](HISTORIA.md).

---

## 7. Modelo de datos (resumen)

| Tabla | Contenido |
|---|---|
| `users` | Cuentas de login (`role` admin/jefe/asesor, `agent_id` opcional, `last_login`) |
| `agents` | Ejecutivos evaluados (`name`, `email`, `campaign`, `active`…) |
| `campaigns` | Campaña con nota de producto (9 campos) + `source` + `active` |
| `calls` | Llamadas subidas; `agent_id` nullable; `uploaded_by`, `campaign_id`, `campaign_type`, `detected_agent_name`, `responsible`, `status` |
| `transcriptions` | Transcripción + segmentos con timestamps (1:1 con call) |
| `analyses` | Scores por dimensión, score global, recomendaciones, resumen (1:1 con call) |
| `rubric_config` | Rúbrica editable: dimensiones con pesos y subcategorías activables (`criteria` JSON) |
| `app_settings` | Configuración global (idioma + umbrales QA `qa_*`) |

Migraciones (Alembic):

- **0001** esquema inicial.
- **0002** detección de ejecutivo (`agent_id` nullable + `detected_agent_name` + `responsible`).
- **0003** rúbrica con subcriterios (`rubric_config.criteria` JSON).
- **0004** campañas (tabla `campaigns` + `calls.campaign_id` + backfill de campañas existentes).
- **0005** roles de usuario (`users.agent_id` FK + backfill `'supervisor'` → `'jefe'`).
- **0006** métricas de conversación (`calls.conversation_metrics` JSON, Fase 2).

---

## 8. Cómo ejecutarlo

Requisito: **Docker Desktop** abierto.

```bash
cd callqa-ai
docker compose up -d --build
```

Levanta 5 servicios (postgres, redis, api, worker, frontend).

- Frontend: <http://localhost:3000>
- API / docs: <http://localhost:8000/docs>
- Cuentas sembradas: `admin@callveroqa.com` (admin) · `jefe@callveroqa.com`
  (jefe) · un **asesor** por cada ejecutivo demo (su email, p. ej.
  `maria@banco.com`). Las contraseñas se **generan al azar** en el primer seed y se
  imprimen una sola vez (`docker compose logs api`); se pueden fijar con
  `SEED_ADMIN_PASSWORD` / `SEED_JEFE_PASSWORD` / `SEED_ASESOR_PASSWORD`.

Tests backend (desde `backend/`): `.\.venv\Scripts\python.exe -m pytest -q`.
Build frontend (desde `frontend/`): `npm run build`.

Para detener: `docker compose down`.

### Para que el análisis con IA funcione

Por defecto basta una **clave de Groq** en `backend/.env` (hace transcripción **y**
análisis, gratis):

```
GROQ_API_KEY=gsk_...
AI_PROVIDER=groq
WHISPER_PROVIDER=groq
```

Sin ella, las llamadas subidas quedan en estado `ERROR` al transcribir.
Claude / OpenAI / Azure son opcionales: cambia `AI_PROVIDER` y pon su API key.

> 💡 También está **desplegado en vivo y gratis** (Vercel + Render); para publicarlo
> tú mismo, ver `DEPLOY_GRATIS.md`.

---

## 9. Despliegue en producción (gratis, coste $0)

- **Frontend** en Vercel: <https://callaibrate.vercel.app>
  (necesita `NEXT_PUBLIC_API_URL=https://callaibrate-api.onrender.com/api/v1`).
- **Backend + PostgreSQL** en Render: <https://callaibrate-api.onrender.com>
  (necesita `GROQ_API_KEY`, `CORS_ORIGINS=https://callaibrate.vercel.app`,
  `PROCESS_INLINE=true`, `JWT_SECRET`).
- Despliegue: `git push origin main` → Vercel y Render redepliegan solos.

> 🔑 **La IA en prod depende de `GROQ_API_KEY` en Render** (variable `sync: false`,
> se pone a mano en el dashboard, **no en el repo**). Si Groq devuelve `401 Invalid
> API Key`, la key de Render está caducada → actualízala con la key válida de
> `backend/.env`. Síntoma: llamadas nuevas en prod quedan en `ERROR` al transcribir.
> El `git push` **NO** actualiza esta key (es secreta y vive solo en Render).

**Cold-start.** El plan gratis de Render duerme el backend tras ~15 min de
inactividad; el arranque en frío (~50 s) puede verse como "error de API".
Mitigado con: GitHub Action `.github/workflows/keepalive.yml` (ping a `/health`
cada 12 min) + **resiliencia en `frontend/lib/api.ts`** (timeout 90 s, reintentos
en cold start, mensaje "activando el servidor"). El PostgreSQL gratis de Render
caduca a los **90 días**.

---

## 10. Verificaciones realizadas

| Verificación | Resultado |
|---|---|
| Build Docker del backend | ✅ |
| Tests del backend (`pytest`) | ✅ 78/78 |
| Migraciones 0001 … 0006 | ✅ aplican sin error |
| Fase 2: métricas de conversación, compliance, endpoints de dashboard | ✅ (tests + E2E) |
| E2E en vivo por rol con Groq real (login, scoping, pipeline) | ✅ local · ⚠️ prod requiere key válida |
| Rediseño premium (build + lint) | ✅ 0 errores |
| Build de producción del frontend | ✅ tipos TS válidos |
| Endpoints API (auth, agents, campaigns, calls, dashboard, config) | ✅ |
| Roles y scoping (admin / jefe / asesor) | ✅ (tests) |
| CORS frontend ↔ backend | ✅ |
| Subida en lote, filtro por fecha, asignación, auto-vínculo | ✅ |
| Campañas (CRUD, extracción de PDF, asistente IA) | ✅ |
| Matching difuso de nombres | ✅ (test unitario) |
| Reintento idempotente y modo inline | ✅ (tests) |

---

## 11. Pendientes / próximos pasos

- [x] **Despliegue en la nube** (frontend → Vercel, backend + PostgreSQL → Render),
      **gratis** y en vivo. Ver `DEPLOY_GRATIS.md`.
- [x] **Groq configurado** (`GROQ_API_KEY` real) haciendo transcripción y análisis
      en producción.
- [x] **Roles** admin/jefe/asesor con scoping y panel "Mi rendimiento".
- [x] **Campañas con nota de producto** (formulario / asistente IA / extracción de PDF).
- [x] **Umbrales QA** configurables y **cold-start** mitigado (keepalive + resiliencia).
- [x] **Analítica de jefe de alto impacto** (alertas accionables, KPIs por campaña,
      top asesores y problemas recurrentes) — Fase 2.
- [x] **Métricas de conversación** (talk/listen ratio, % silencio, monólogos,
      velocidad de habla) derivadas de la transcripción — Fase 2 (migración 0006).
- [x] **Vista de asesor enriquecida** (percentil anónimo en la campaña, "qué cambiar"
      con evidencia, cumplimiento por campaña) — Fase 2.
- [x] **Rediseño premium de indicadores y UX** (gauge, sparklines, donut, delta chips,
      tabla de campañas, alertas por severidad).
- [ ] **⚠️ Actualizar `GROQ_API_KEY` en Render** (dashboard, `sync: false`) con la key
      válida para que la IA procese en producción. Es lo único que bloquea la IA en prod.
- [x] **Reproductor de audio sincronizado** con la transcripción (endpoint
      `GET /calls/{id}/audio` + `components/calls/transcript-player.tsx`).
- [x] **Exportación CSV** del reporte del equipo (`GET /dashboard/report.csv` +
      botón en el dashboard, respeta los filtros activos).
- [x] **Rebrand a CallVeroQA** (`docs/BRAND.md` + `DESIGN.md`).
- [x] **Endurecimiento de seguridad:** contraseñas de seed aleatorias con rotación de
      las publicadas, guardarraíl de `JWT_SECRET` en producción, `datetime.utcnow()`
      corregido.
- [ ] Antes de producción real: cerrar **[`COMPLIANCE_CHECKLIST.md`](COMPLIANCE_CHECKLIST.md)**
      (validaciones de Compliance, DPO y Seguridad).
- [x] **Renombrado de la infraestructura** a `callaibrate-api` / `callaibrate-db` y
      URLs nuevas. Ver **[`RENOMBRADO_INFRA.md`](RENOMBRADO_INFRA.md)**.
- [~] **Copias de seguridad de la base de datos.** Workflow
      `.github/workflows/backup-db.yml` listo (volcado diario, artefacto a 30 días).
      **Falta** definir el secreto `DATABASE_URL` en GitHub y probar una restauración.
- [x] **Vigilancia real del backend.** El keepalive ya **falla** (y avisa) cuando
      `/health` no responde; antes terminaba en `|| true` y se tragaba la caída.
- [ ] **Almacenamiento persistente de audios** (S3): el disco del contenedor es efímero
      y los audios se pierden en cada redespliegue.

---

## 12. Historial de iteraciones

1. **Generación inicial** del backend completo (FastAPI + Celery + modelo de
   datos + tests) a partir de un prompt maestro de generación (spec de origen).
2. **Frontend** Next.js con todas las páginas y el sistema de diseño inicial.
3. **Verificación** con Docker: build, tests, stack levantado.
4. **Rediseño de flujo**: subida en lote, detección del ejecutivo por IA,
   matching difuso, asignación posterior, filtro por fecha (con tests adicionales).
5. **Reestilo** a una identidad corporativa púrpura.
6. **Reestilo** a la segunda identidad visual del proyecto (ver `HISTORIA.md`).
7. **Optimización**: frontend a modo producción (salida standalone) y
   reorganización en este **monorepo** con un único `docker-compose.yml`.
8. **Migración a Groq** como proveedor por defecto (Whisper large v3 + Llama 3.3
   70B, coste $0); el patrón factory mantiene Claude/OpenAI/Azure como opciones.
9. **Rúbrica editable** con subcategorías y categorías que se pueden añadir/eliminar
   (migración `0003`); el prompt de la IA pasa a ser **dinámico**.
10. **Diarización por LLM** (por contenido), dejando la heurística de pausas como
    fallback; filtros del dashboard (campaña/ejecutivo/fechas).
11. **Despliegue gratis en vivo**: Vercel (frontend) + Render (backend + PostgreSQL),
    con **procesamiento inline** (`PROCESS_INLINE=true`) para correr sin Celery/Redis.
12. **Campañas con nota de producto** (migración `0004`): entidad `Campaign`,
    extracción de la oferta desde PDF (pypdf + LLM) y formulario con asistente IA;
    la nota se inyecta en el prompt de análisis.
13. **Rebrand a la identidad corporativa de entonces** (ver `HISTORIA.md`), que
    sustituyó a la anterior. Hoy las dos están obsoletas.
14. **Roles admin/jefe/asesor** (migración `0005`) con scoping, login de asesor,
    panel "Mi rendimiento" y **umbrales QA** configurables.
15. **Limpieza de lenguaje a "vista previa para evaluación"** (se elimina el de
    "demo interna"; sin credenciales demo en login ni contraseñas en el seed) y
    **fix de cold-start** (keepalive + resiliencia en el frontend).
16. **Fase 2 — Analítica de alto impacto** (migración `0006`): métricas de
    conversación deterministas, compliance de nota de producto, endpoints de
    dashboard (by-campaign, alerts, top-recommendations, percentil, recomendaciones)
    y vistas enriquecidas de jefe y asesor. +17 tests (total **78**).
17. **Rediseño premium de indicadores y UX**: sistema de dataviz de marca
    (`components/dashboard/viz.tsx`) — gauge de score, sparklines, donut, delta
    chips, tabla de campañas, alertas por severidad, toolbar segmentado — fiel a la
    la identidad de entonces. Banner de prototipo **retirado** de la UI.
18. **Despliegue de Fase 2 + rediseño a producción** (Vercel + Render) y verificación
    (78 tests + suite E2E 13/13 local y prod). Pendiente: actualizar la
    `GROQ_API_KEY` de Render para reactivar la IA en producción.
19. **Dos repos** (privado `callqa-ai` completo + público `callqa` limpio, ver
    `AGENTS.md §16`) y **auditoría de coherencia**: se eliminó código muerto
    (`require_role`, `kpi-card`, `seed_rubric`, settings de IA que no se leían,
    artefactos Railway), se alinearon comentarios/docstrings al estado real y se
    consolidaron los specs de origen (01–07) en los docs canónicos.

20. **Rebrand a CallVeroQA + mejoras**: nueva identidad (`docs/BRAND.md` como fuente
    de verdad) con paleta paper/ink y acentos rust/gold, tipografías Manrope / Inter /
    IBM Plex Mono, wordmark waveform como componente SVG, radios de 8/6 px en lugar de
    los contenedores achaflanados y titulares en caso frase. Además: **reproductor de
    audio sincronizado** con la transcripción (endpoint de audio nuevo), **exportación
    CSV** del reporte de equipo, **contraseñas de seed aleatorias** con rotación de las
    que llegaron a estar publicadas, **guardarraíl de `JWT_SECRET`** en producción,
    `datetime.utcnow()` corregido y `COMPLIANCE_CHECKLIST.md`. +9 tests (total **87**).

---

## 13. Casos de uso, reglas de negocio y gobernanza (consolidado)

> Resumen de los specs de origen (visión, requerimientos, arquitectura, pitch), ya
> consolidados aquí. La fuente de verdad del comportamiento es el código; el detalle
> operativo vive en `AGENTS.md`.

**Casos de uso (esencia).** Un manager (admin/jefe) sube **audios en lote** indicando
campaña, comentario y responsable; por cada llamada la IA **transcribe**, **enmascara
PII**, **detecta y empareja al ejecutivo** (matching difuso), y **evalúa** contra la
rúbrica dinámica inyectando la **nota de producto** de la campaña. El manager consulta
el **dashboard** (KPIs, alertas, campañas, ranking, conversación), el **detalle** de
cada llamada, descarga el **reporte PDF**, y gestiona ejecutivos, campañas, rúbrica y
umbrales. El **asesor** entra a **"Mi rendimiento"** y solo ve lo suyo (percentil
anónimo, qué cambiar con evidencia, cumplimiento por campaña).

**Reglas de negocio clave.**
- **Bandas de score** (color): `0–59` rojo · `60–79` aceptable · `80–100` excelente.
- **Umbrales QA** configurables por manager (`app_settings`): objetivo 90, asesor bajo
  80, llamada roja 60, mínimo de llamadas para ranking 5, alerta de caída 5 puntos.
- **Rúbrica dinámica**: dimensiones y subcriterios activables; los **pesos suman 100**;
  las claves las genera un slug; el prompt puntúa las dimensiones reales.
- **Roles/scoping**: `admin` y `jefe` = gestión + analítica global (`is_manager`);
  `asesor` solo su ficha, sus llamadas y su panel. `require_manager` protege gestión.
- **Matching difuso** de nombres de ejecutivo (umbral de similitud 0.82).
- **Enmascarado de PII** best-effort (regex) **antes** de enviar texto al LLM.
- **Campañas con nota de producto** (9 campos) → cumplimiento (frases obligatorias,
  claims prohibidos) evaluado de forma determinista y por el LLM.

**Gobernanza y compliance (banca).** El enmascarado es *best-effort*,
**no** garantía, y el **audio crudo sale a Groq (EE. UU.)**. Para **datos reales de
clientes** se requiere: transcripción y análisis **on-prem / Azure** (el factory ya lo
soporta por configuración) y **aprobación previa de DPO/CISO/Compliance**. Roadmap por
fases hacia producción real (validaciones de Compliance/DPO/Seguridad; migración a
**Azure OpenAI + Azure AI Speech**).

**Valor.** Automatiza el QA que hoy es manual y por muestreo (cobertura 100 % vs. ~2 %),
con **coste $0** en el entorno actual (Groq gratis + tiers gratis de Vercel/Render) y
**portabilidad** a la infraestructura de Indra solo por configuración.
