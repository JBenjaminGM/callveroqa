# AGENTS.md — Guía para IAs y desarrolladores

> **Lee esto primero.** Es el punto de entrada para entender el proyecto y hacer
> cambios sin contexto previo. Es la **fuente de verdad del estado ACTUAL**.
> Los demás archivos de esta carpeta `docs/` son la especificación de origen
> (algunos ya históricos; ver el mapa en §12).
>
> **Rutas:** las rutas a código (`backend/...`, `frontend/...`) son relativas a la
> **raíz del repositorio** (este archivo vive en `docs/`).

---

## 1. Qué es

**CallVeroQA**: plataforma web de **Quality Assurance automatizado con IA** para
call centers bancarios. Un manager sube audios de llamadas; la IA las
**transcribe** (Groq Whisper large v3), **enmascara la PII** (best-effort) y las
**analiza con un LLM** (Groq Llama 3.3 70B) contra una **rúbrica dinámica**, y
devuelve scores por dimensión, un **score global ponderado**, recomendaciones
accionables y un **reporte PDF**. Sector: **banca**.

> ⚠️ **No utilizar con datos reales de clientes sin la aprobación previa de
> Compliance.** Por decisión del responsable, el **banner visible de "vista previa /
> entorno de evaluación" se RETIRÓ de la UI** (la plataforma se presenta como producto
> acabado). Como salvaguarda interna **se conservan** el header HTTP `X-Prototype-Notice`
> (`Evaluation environment - Do not use with real customer data`) y el log JSON
> `environment="evaluation"`.

## 2. Estado actual (en vivo)

> ⚠️ **Producción reconstruida (sept. 2026).** La PostgreSQL free de Render **caducó y
> se eliminó**; el backend llevaba dos meses muriendo al arrancar y **los datos de
> producción se perdieron**. Se recreó como `callveroqa-api` + `callveroqa-db`. Ver
> [`RENOMBRADO_INFRA.md`](RENOMBRADO_INFRA.md). **Volverá a caducar a los 30 días** si
> se sigue en el plan gratuito.
>
> 🔑 **`GROQ_API_KEY`:** la pone el usuario en Render → `callveroqa-api` →
> **Environment**. Es `sync: false` (solo en Render, nunca en el repo); `git push` NO la
> actualiza. La clave filtrada en `aeda304` está **revocada**. Ver §10.

- **Repo COMPLETO:** `github.com/JBenjaminGM/callveroqa` (público) (rama `main`, fuente de verdad: código + `docs/` + `ops/`). **Push a `main` ⇒ redeploy automático** en Vercel y Render.
- **Repo LIMPIO (público):** `github.com/JBenjaminGM/callveroqa-public` — copia derivada solo con código funcional + un `README.md` curado (sin `docs/`, `AGENTS.md`, `CLAUDE.md`, `ops/`; historial propio, sin rastro de autoría). Se genera con **`ops/publish-clean.ps1`** (ver §16). NO se trabaja ahí a mano.
- **Frontend (Vercel):** https://callveroqa.vercel.app — dashboard con **rediseño premium de indicadores** (Fase 2).
- **Backend (Render):** https://callveroqa-api.onrender.com (`/health`, `/docs`)
- **Cuentas sembradas:** `admin@callveroqa.com` (admin), `jefe@callveroqa.com` (jefe) y un **asesor por cada ejecutivo demo** (el email del ejecutivo, p. ej. `maria@banco.com`). Las **contraseñas se generan al azar** en el primer seed y se imprimen **una sola vez** (`docker compose logs api`); se pueden fijar con `SEED_ADMIN_PASSWORD` / `SEED_JEFE_PASSWORD` / `SEED_ASESOR_PASSWORD`. El seed **rota** cualquier cuenta que aún use una de las contraseñas que llegaron a estar publicadas.
- **Coste de operación: $0** (Groq gratis + tiers gratis de Vercel/Render).
- **Workflows de GitHub Actions:** `keepalive.yml` (ping a `/health` cada 12 min; **falla y avisa** si no responde) y `backup-db.yml` (volcado diario con `pg_dump`; necesita el secreto `DATABASE_URL` con la *External Database URL* de Render).
- **Ubicación de trabajo local:** `C:\Users\master\dev\callveroqa` (NO la copia de OneDrive — Docker falla desde OneDrive por archivos "solo en la nube").

## 3. Arquitectura

```
Navegador ─HTTPS→ Frontend (Next.js·Vercel) ─REST→ Backend (FastAPI·Render)
                                                       ├─→ PostgreSQL (Render)
                                                       └─→ Groq (Whisper + Llama)
```

- **En la nube** el backend procesa la llamada **dentro de la propia API**
  (`PROCESS_INLINE=true`, vía `BackgroundTasks`) — **sin Celery/Redis**, para caber
  en el tier gratis de Render (no ofrece workers).
- **En local (`docker-compose`)** se usa el modo "producción" con **Celery + Redis**
  (un worker procesa las tareas). `PROCESS_INLINE` queda en `false`.
- **GitHub** dispara los despliegues. **No hay CI propio**; Vercel/Render construyen al hacer push.
- **Cold-start (tier gratis de Render):** el backend **duerme tras ~15 min** de
  inactividad; el arranque en frío tarda **~50 s** (puede verse como "error de API").
  Mitigado con: **GitHub Action** `.github/workflows/keepalive.yml` (ping a `/health`
  cada 12 min) y **resiliencia en `frontend/lib/api.ts`** (timeout 90 s, reintentos
  en cold start, mensaje "activando el servidor"). El **PostgreSQL gratis caduca a los 90 días**.

## 4. Stack

| Capa | Tecnologías |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind, TanStack Query, Zustand, Recharts, Axios, **Manrope / Inter / IBM Plex Mono** |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, slowapi |
| Cola (solo local) | Celery 5 + Redis |
| Base de datos | PostgreSQL 15 |
| IA — transcripción | **Groq** · Whisper large v3 |
| IA — análisis | **Groq** · Llama 3.3 70B (`AI_PROVIDER=groq`) · factory → claude / openai / azure |
| PDF | reportlab (genera el reporte) · pypdf (lee la nota de producto de campañas) |
| Seguridad | JWT (python-jose), bcrypt (passlib), CORS lista blanca |
| Almacenamiento | local / S3 opcional (boto3) |
| Infra | Docker, GitHub, Vercel (frontend), Render (backend+PostgreSQL) |

## 5. Mapa del repositorio (dónde está cada cosa)

```
backend/
  app/
    main.py            App FastAPI: CORS, logging JSON, routers, /health, header de "vista previa"
    config.py          Settings desde env. ai_provider=groq (default), process_inline,
                       y normaliza postgres:// → postgresql:// (Render/Heroku)
    database.py        engine + SessionLocal + get_db()
    dependencies.py    get_current_user (valida el JWT), require_manager (admin/jefe),
                       is_manager (helper de rol)
    models/            SQLAlchemy: user (role + agent_id), agent, campaign, call, transcription,
                       analysis, review (nota humana), acknowledgement (respuesta del asesor),
                       settings.py (RubricConfig con `criteria` JSON + AppSettings)
    schemas/           DTOs Pydantic: auth, agent, campaign, call, analysis, dashboard, config,
                       review, coaching
    routers/           auth, agents, campaigns, calls, dashboard, config, calibration, coaching
    services/          analysis_service.py  → factory IA (ClaudeProvider/OpenAIProvider/
                                               GroqLLMProvider(=OpenAI compatible)/Azure) + calculate_global_score
                       transcription_service.py → factory STT (Groq/local/azure) +
                                               add_speaker_diarization (heurística de FALLBACK)
                       masking_service.py    → enmascarado best-effort (regex)
                       name_matching.py      → matching difuso de nombres de ejecutivo
                       campaign_service.py   → CRUD de campañas + nota de producto (build_product_note_text)
                       campaign_ai.py        → extracción de la oferta desde PDF (pypdf+LLM) + asistente IA
                       conversation_metrics_service.py → métricas deterministas ($0) de la
                                               conversación (talk-ratio, silencio, WPM, turnos)
                       compliance_service.py → cobertura de frases obligatorias / claims prohibidos
                       dashboard_service.py  → KPIs por campaña, alertas, recomendaciones, percentil
                       review_service.py     → score humano ponderado + acuerdo IA-humano por dimensión
                       coaching_service.py   → a quién escuchar hoy + peticiones de revisión abiertas
                       call_service.py, agent_service.py, auth_service.py,
                       storage_service.py (local/s3), pdf_service.py
    tasks/
      call_tasks.py    process_call + _run_pipeline (EL pipeline; ver §6)
      celery_app.py    config de Celery (solo se usa en modo no-inline)
    prompts/
      __init__.py      get_analysis_prompt(segments, rubric, language, campaign)
      analysis_es.py / analysis_en.py  → prompt DINÁMICO: lista subcriterios activos, INYECTA la
                       nota de producto de la campaña y genera "dimension_scores" con las claves reales
    utils/             security.py (JWT/bcrypt), audio.py (validación de archivos)
  alembic/versions/    0001 esquema, 0002 detección ejecutivo, 0003 rubric_config.criteria,
                       0004 campañas, 0005 roles de usuario, 0006 conversation_metrics,
                       0007 server_default de users.role → 'jefe', 0008 usuarios de solo
                       lectura, 0009 revisiones humanas, 0010 acuses de recibo, 0011 evidencia y criterios críticos, 0012 usuarios activables, 0013 retención de audios, 0014 motivo de la llamada
  scripts/seed_data.py admin + jefe + asesores + rúbrica (subcriterios) + settings (umbrales QA) +
                       3 ejecutivos demo + 3 campañas demo (NO imprime contraseñas)
  scripts/seed_demo.py 67 llamadas en 90 días + 22 revisiones humanas + 6 respuestas de
                       asesores. Sin IA y con semilla fija: siempre da lo mismo y cuesta $0
  tests/               187 tests (conftest = SQLite en memoria, todo lo externo mockeado)
  Dockerfile           multi-stage. CMD = alembic upgrade + seed + uvicorn (lo usa Render)
  .env / .env.example  (.env está gitignorado)
frontend/
  app/                 App Router: login/, (main)/{dashboard, mi-panel, calls, calls/new,
                       calls/[id], agents, agents/[id], campaigns, settings}, layout, providers
  components/          ui/ (button, input, card, badge, select, feedback…), layout/, charts/, dashboard/
  lib/                 api.ts (axios + interceptores 401 + resiliencia cold-start), auth.ts (Zustand +
                       JWT en localStorage; guarda role/agent_id), queries.ts (TODOS los hooks de
                       TanStack Query), utils.ts (dimensionLabel, formatos)
  types/index.ts       Tipos TS que reflejan la API
  components/brand/    logo.tsx — Waveform + Wordmark (única fuente del logotipo)
  public/favicon.svg   ícono waveform de la marca
  app/globals.css      ★ COLORES CANÓNICOS (variables CSS CallVeroQA, modo claro+oscuro)
  tailwind.config.ts   mapea los colores a las variables CSS
docs/                  00–07 + DESIGN.md (especificación de origen; ver §12)
.github/workflows/     keepalive.yml (ping a /health cada 12 min para mitigar el cold-start)
docker-compose.yml     stack local completo (postgres, redis, api, worker, frontend)
render.yaml            blueprint de Render (backend Docker + PostgreSQL, PROCESS_INLINE=true)
DEPLOY_GRATIS.md       guía de despliegue gratis (Vercel + Render)
CHANGELOG.md           historial de cambios
```

## 6. El pipeline de análisis (`backend/app/tasks/call_tasks.py`)

`process_call(call_id)` → `_run_pipeline`:
1. **Idempotencia:** borra transcripción/análisis previos (permite reintentar sin violar `UNIQUE(call_id)`).
2. **Transcribe** el audio con el proveedor STT (Groq Whisper) → texto + segmentos.
3. **Diarización heurística de FALLBACK** (`add_speaker_diarization`, por pausas).
4. Guarda la **transcripción**.
5. **Enmascara** datos sensibles de cada segmento (best-effort).
6. Lee la **rúbrica** (con subcriterios) y la **nota de producto de la campaña**, y construye el **prompt dinámico**.
7. **LLM** (Groq Llama) → `dimension_scores`, `summary`, `recommendations`, `detected_agent_name` y `diarization`.
8. **Aplica la diarización del LLM** (por contenido) sobre los segmentos (corrige la heurística).
8b. **Métricas de conversación** deterministas (`conversation_metrics_service`) sobre los segmentos ya diarizados → `Call.conversation_metrics` (talk-ratio, silencio, WPM, turnos).
9. **calcula el score global** ponderado; **detecta+empareja** al ejecutivo (matching difuso).
10. Guarda el **análisis** → estado `DONE`.
- Si algo falla: `db.rollback()` y marca `ERROR` con el detalle.

## 7. Roles y autenticación

Tres roles. **admin** y **jefe** tienen los **mismos permisos por ahora** (gestión +
analítica global; helper `is_manager`); **asesor** solo ve **su propio rendimiento**.

- **Modelo:** `User.role` (`'admin'|'jefe'|'asesor'`, default `'jefe'`) + `User.agent_id`
  (FK a `agents`, vincula al asesor con su ficha de ejecutivo; `NULL` para admin/jefe).
- **Protección:** la dependencia `require_manager` cubre los endpoints de gestión.
- **Asesor:** solo ve su ficha, sus llamadas y su panel "Mi rendimiento"; recibe **403**
  al intentar el dashboard global, subir/asignar/reintentar/eliminar llamadas, settings
  o gestionar ejecutivos.
- **Crear el login del asesor:** `POST /agents/{id}/login` (lo crea un manager; vincula
  `User`↔`Agent`).
- **Frontend:** navegación y redirección por rol (asesor → `/mi-panel`; admin/jefe →
  `/dashboard`), guard por rol y página "Mi rendimiento".

## 8. Cómo correr y testear (local, Windows sin admin)

- **Stack completo (Docker):** `cd C:\Users\master\dev\callveroqa && docker compose up -d --build`
  (5 servicios: postgres, redis, api, worker, frontend)
  → app http://localhost:3000 · API http://localhost:8000/docs · login `admin@callveroqa.com` con la contraseña que imprime el seed (`docker compose logs api`).
  Apagar: `docker compose down`.
- **Tests backend (187):** desde `backend/`, `.\.venv\Scripts\python.exe -m pytest -q`
  (el venv ya tiene `requirements.txt`; SQLite en memoria, sin red).
- **Build frontend:** desde `frontend/`, `npm run build`.
- **Desplegar:** `git push origin main` (Vercel + Render redepliegan solos).
- **Herramientas:** Python 3.11 (user install), Node v24 portátil (`%LOCALAPPDATA%\node-portable\...`), Docker Desktop. La consola es cp1252 → al ejecutar Python con Unicode usar `$env:PYTHONIOENCODING="utf-8"`.

## 9. Variables de entorno clave (`backend/.env`)

| Variable | Valor | Nota |
|---|---|---|
| `GROQ_API_KEY` | `gsk_...` | Transcripción **y** análisis (gratis) |
| `AI_PROVIDER` | `groq` | factory: `groq` \| `claude` \| `openai` \| `azure` |
| `AI_MODEL_GROQ` | `openai/gpt-oss-120b` | El catálogo de Groq cambia; si da 404 `model_not_found`, elegir otro modelo de producción |
| `WHISPER_PROVIDER` | `groq` | |
| `PROCESS_INLINE` | `false` local / `true` en Render | Sin worker Celery cuando es `true` |
| `DATABASE_URL` | postgres… | Se normaliza `postgres://`→`postgresql://` |
| `JWT_SECRET` | cadena larga | Cambiar en producción |
| `CORS_ORIGINS` | URL(s) del frontend | Lista blanca separada por comas (en Render: `https://callveroqa.vercel.app`) |

> En **Vercel** se necesita `NEXT_PUBLIC_API_URL=https://callveroqa-api.onrender.com/api/v1`.

## 10. Decisiones clave y *gotchas* (LÉELO antes de tocar)

- **IA = Groq por defecto.** Para usar Claude/OpenAI/Azure: cambiar `AI_PROVIDER` + poner su API key. El código YA lo soporta (factory en `analysis_service.py`). Portar a **Azure OpenAI + Azure AI Speech** (producción Indra) = solo configuración.
- **🔑 `GROQ_API_KEY` en producción (Render) es `sync: false`** → vive SOLO en el dashboard de Render, **nunca en el repo**, y `git push` NO la cambia. Si Groq devuelve `401 Invalid API Key`, la key de Render caducó (p. ej. tras rotarla por la filtración del commit `aeda304`): actualízala en Render → `callveroqa-api` → Environment con la key válida de `backend/.env`. Síntoma: llamadas nuevas en prod en `ERROR` al transcribir. Diagnóstico rápido: `curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer <key>"` (200 = válida).
- **El proveedor de IA/transcripción lo fija SIEMPRE la env var** (`AI_PROVIDER`/`WHISPER_PROVIDER`), **nunca la BD**. `/config/settings` (GET) lo reporta desde la env var (no miente). En BD (`app_settings`/`SettingsUpdate`) solo se guarda `default_language` + los umbrales `qa_*`; NO reintroduzcas `ai_provider`/`whisper_provider` como settings de BD (no se leerían).
- **Umbrales QA configurables** (en `app_settings`, editables solo por manager): `qa_target_score=90`, `qa_low_agent_threshold=80`, `qa_red_call_threshold=60`, `qa_min_calls_ranking=5`, `qa_trend_drop_alert=5`.
- **Campañas con nota de producto:** la entidad `Campaign` lleva una **nota de producto de 9 campos** (producto/servicio, descripción de la oferta, beneficios clave, precio/condiciones, requisitos del cliente, frases obligatorias, claims prohibidos, público objetivo, notas). Se crea por formulario (con asistente IA), o **subiendo un PDF** que la IA parsea (`pypdf`+LLM) y autocompleta; lo que no encuentre se pide en el formulario. La nota **se INYECTA en el prompt de análisis** para evaluar si el ejecutivo ofreció la oferta correcta (integrado en los criterios existentes promotions/compliance). `Call.campaign_id` (FK; se conserva `campaign_type` texto por compatibilidad y para filtros del dashboard).
- **Enmascarado = best-effort**, NO garantía. Los regex cazan dígitos/algunos números dictados, pero **el audio crudo sale a Groq (EE. UU.)**. Para datos reales: transcripción on-prem/Azure + DPO/CISO.
- **Diarización (quién habla):** la hace el **LLM por contenido**; la heurística de pausas es solo fallback. Es aproximada en turnos ambiguos. Fiable de verdad = speaker-ID acústico (Azure Speech / pyannote).
- **Rúbrica DINÁMICA:** editable con subcriterios activables y **categorías que se pueden añadir/eliminar**. `PUT /config/rubric` es **reemplazo completo** (crea/actualiza/borra; genera la clave con slug). El prompt construye `dimension_scores` con las claves reales → las categorías nuevas se puntúan solas. En el frontend, `dimensionLabel()` (lib/utils.ts) humaniza claves desconocidas.
- **Dashboard:** filtros campaña/ejecutivo/fechas/periodo; endpoint `/dashboard/campaigns`. Las fechas se comparan con `datetime.utcnow()` (naïve) porque la BD guarda timestamps naïve — NO usar `datetime.now(timezone.utc)` ahí (rompía con un `TypeError`).
- **Colores = identidad CallVeroQA:** la fuente de verdad de la **marca** es `docs/BRAND.md`; la **implementación** canónica es `frontend/app/globals.css` + `tailwind.config.ts`. `DESIGN.md` explica cómo se aplica. **Las identidades visuales anteriores están OBSOLETAS** (cuáles fueron, en `docs/HISTORIA.md`): si aparece una de sus paletas, tipografías o clases en el código, es deuda.
- **Despliegue:** el arranque (migraciones+seed+uvicorn) vive en el **CMD del Dockerfile** (no en `render.yaml`) para evitar que Render parta mal el comando con comillas (daba exit 127).
- **Cold-start:** ver §3 (keepalive + resiliencia en `lib/api.ts`).
- **El límite del login se cuenta por IP + cuenta, no por IP** (`app/limiter.py`). Un call center entero sale por una IP pública: contando solo por IP, cinco fallos de una persona dejaban al equipo fuera 15 minutos.
- **Retención** (`services/retention_service.py`): caduca el **audio**, nunca la transcripción ni la nota. `retention_audio_days=0` (por defecto) = no caduca. La purga **no borra un archivo que otra llamada vigente comparte** — el seed de demostración reutiliza seis audios entre 67 llamadas y sin esa comprobación dejaba mudas llamadas recientes. Corre sola al listar llamadas, como mucho cada 6 h.
- **Suprimir datos de una persona es de `require_admin`**, no de manager, y es irreversible: `DELETE /agents/{id}` solo desactiva; `DELETE /agents/{id}/data` borra todo lo suyo. No confundirlos.
- **Motivos de llamada** (`services/topic_service.py`): el riesgo no es detectarlos, es que se fragmenten («cobro duplicado» / «Cobro duplicado» / «duplicidad de cobro» serían tres barras del panel). Por eso al analizar se le pasa a la IA el catálogo ya usado para que reutilice, y al guardar se normaliza (espacios, mayúsculas, acentos) y se busca un equivalente. **Si añades una fuente nueva de motivos, pásala por `resolve_topic`.**
- **Nunca se puede quedar la plataforma sin un administrador activo** (`services/user_service.py`), ni desactivarse uno mismo. La cuenta demo (`is_readonly`) no se administra desde la API.
- **Evidencia y criterios críticos** (`services/evidence_service.py`, migración 0011): todo lo que el LLM devuelve en `dimension_evidence` / `critical_failures` se **sanea contra la rúbrica** — un crítico que la rúbrica no marca como tal se descarta. Con un crítico incumplido, `global_score = 0` y `uncapped_score` guarda la nota real. **Regla:** calibración (revisión humana, panel de acuerdo) y medias de coaching usan `rubric_score(analysis)`, **nunca** `global_score` a pelo; si no, el 0 del auto-fail se lee como desacuerdo. Para filtrar suspendidas usa `uncapped_score IS NOT NULL`: las columnas JSON guardan `None` como `null` JSON, no como NULL de SQL.

## 11. Diseño = identidad CallVeroQA

UI rebrandeada a **CallVeroQA**. Las identidades visuales anteriores quedaron
**obsoletas**; qué eran se cuenta en [`HISTORIA.md`](HISTORIA.md), que es el único
sitio del repositorio donde se nombran.

- **Fuente de verdad de la marca:** **`docs/BRAND.md`**. Cualquier cambio visual empieza ahí.
- **Paleta:** **paper `#F5F1E8`** + **ink `#2A2420`** dominan; **rust `#B8441F`** es el acento de marca y **gold `#A67C27`** el secundario. `success`/`danger` son funcionales, no decorativos.
- **Tipografía:** **Manrope** (titulares), **Inter** (cuerpo/UI), **IBM Plex Mono** (solo datos numéricos), vía `next/font/google`.
- **Wordmark:** `frontend/components/brand/logo.tsx` (`<Waveform />`, `<Wordmark />`). El fragmento "Vero" siempre en rust.
- **Radios:** `rounded-card` (8px) en contenedores, `rounded-control` (6px) en controles. `rounded-full` solo en avatares, puntos y barras. Las clases de forma de la identidad anterior ya no existen.
- **Titulares en caso frase** con una palabra clave opcional en rust (`<span class="hl">`).
- **Modo claro por defecto** + **modo oscuro derivado** (ver addendum de `BRAND.md`).
- **Sidebar** siempre en ink (color literal, porque el token se invierte en oscuro), con el wordmark en negativo.
- **Implementación canónica del color:** `frontend/app/globals.css` + `tailwind.config.ts`.
- **Sistema de dataviz premium (Fase 2):** `frontend/components/dashboard/viz.tsx`
  centraliza las primitivas de visualización fieles a la marca — `ScoreGauge` (anillo
  de score), `Sparkline`, `Donut`, `MiniProgress`, `DeltaPill`, `BrandTooltip` —; más
  `StatCard` (KPI con delta + sparkline), `SectionHeader`/`Eyebrow`
  (`components/ui/section.tsx`), `CallsTrendChart` (`trend-chart.tsx`) y los compuestos
  de `insights.tsx` (alertas, tabla por campaña, percentil, etc.). **Reutilízalos** en
  vez de crear gráficos sueltos; todos usan las variables CSS para tema claro/oscuro.
- **Banner de prototipo RETIRADO** de la UI (decisión del responsable); el header HTTP
  `X-Prototype-Notice` y el log `environment="evaluation"` se conservan como salvaguarda interna.

## 12. Endpoints y modelo de datos

**Prefijo `/api/v1`; todo requiere JWT salvo `POST /auth/login`.** `[manager]` =
admin/jefe (`require_manager`); `[scoped]` = el asesor solo ve lo suyo.

- **auth:** `login` [rate limit 5/15min], `refresh`, `logout`, `me` (devuelve `role` y `agent_id`).
- **agents:** `GET` lista [scoped: asesor solo su ficha], `POST` crear [manager], `POST /{id}/login` [manager], `GET /{id}` [scoped], `PUT`/`DELETE` [manager].
- **campaigns:** `GET`/`POST`/`GET /{id}`/`PUT`/`DELETE` + `POST /extract` (PDF) + `POST /assist` (IA).
- **calls:** `POST` subir + `POST /batch` [manager], `GET` lista [asesor solo las suyas; `?q=` busca en la transcripción y devuelve `match_snippet`, `?critical=true` solo suspendidas], `GET /{id}` [scoped], `GET /{id}/status`, `PUT /{id}/assign` [manager], `POST /{id}/retry` [manager], `GET /{id}/report.pdf` [scoped], `DELETE` [manager].
- **dashboard:** `GET /topics` [manager] (motivos de llamada: volumen, nota, % rojas y suspendidas), `GET /summary` [manager, +`team_dimension_averages`/`avg_duration_seconds`/`red_call_count`/`conversation_summary`], `GET /campaigns` [manager], `GET /by-campaign` [manager], `GET /alerts` [manager], `GET /top-recommendations` [manager], `GET /agents/{id}` [scoped], `GET /agents/{id}/percentile` [scoped], `GET /agents/{id}/recommendations` [scoped].
- **users** [manager]: `GET`/`POST /users`, `PATCH /users/{id}` (nombre, rol, activo), `POST /users/{id}/reset-password`. El cambio de la contraseña propia es `POST /auth/change-password` (cualquiera).
- **agents:** además `DELETE /agents/{id}/data` [**admin**] — supresión total de los datos de esa persona.
- **config:** `GET`/`PUT /rubric` (PUT [manager]), `GET /settings`, `PUT /settings` [manager, incluye umbrales QA].

**Modelo de datos:** `users` (id, email, password_hash, name, **role**, **agent_id**,
created_at, last_login); `agents` (ejecutivos evaluados; name, email, campaign,
active…); `campaigns` (**nota de producto de 9 campos** + source + active); `calls`
(agent_id nullable, uploaded_by, **campaign_id**, campaign_type, detected_agent_name,
responsible, status, audio, **conversation_metrics JSON**…); `transcriptions` (full_text, segments con timestamps;
1:1 con call); `analyses` (global_score, dimension_scores, recommendations, summary;
1:1 con call); `rubric_config` (dimension_key, dimension_name, weight, **criteria JSON**
activable); `app_settings` (clave-valor: idioma + **umbrales QA `qa_*`**).

## 13. Cómo hacer cambios comunes

- **Añadir un endpoint:** crea/edita en `app/routers/`, regístralo en `app/main.py`, añade su schema en `app/schemas/` y, si toca BD, su modelo + migración Alembic. Protege con `require_manager` si es de gestión.
- **Cambiar la BD:** edita el modelo en `app/models/`, luego `alembic revision -m "..."` (o crea el archivo a mano siguiendo `0005`), y `alembic upgrade head`. El `seed_data.py` corre en cada arranque (idempotente).
- **Cambiar/añadir proveedor IA:** `app/services/analysis_service.py` (análisis) o `transcription_service.py` (STT) — patrón factory. Variable `AI_PROVIDER`/`WHISPER_PROVIDER`.
- **Tocar el prompt de la IA:** `app/prompts/analysis_es.py` / `_en.py` (es dinámico según la rúbrica e inyecta la nota de producto de la campaña).
- **Cambiar colores/diseño:** primero `docs/BRAND.md`, luego `frontend/app/globals.css` + `tailwind.config.ts` — se propaga a toda la app y a los gráficos.
- **Añadir una página/hook frontend:** página en `frontend/app/(main)/...`, hooks de datos en `frontend/lib/queries.ts`, tipos en `frontend/types/index.ts`.
- **Desplegar cambios:** solo `git push origin main` (Vercel + Render redepliegan).

## 14. Tests

187 tests en `backend/tests/` (pytest, SQLite en memoria, externos mockeados). Cubren
auth, **roles y scoping (admin/jefe/asesor)**, agentes, **campañas**, cálculo de score,
enmascarado, matching difuso, **idempotencia del reintento**, **modo inline**, **umbrales
QA**, **creación del login del asesor**, la **analítica** (métricas de conversación,
compliance de nota de producto y endpoints de dashboard con scoping), la **calibración**
(que la nota de la IA no se pisa, que la sesión a ciegas no filtra el score, y que el
informe de acuerdo distingue sesgo de desviación media) y el **cierre del ciclo** (quién
puede firmar un acuse, reapertura de peticiones y orden de «a quién escuchar hoy»). **No**
cubren el end-to-end real con APIs (eso se valida con audios reales). Correr antes de cada cambio.

## 15. Mapa de documentación

Toda la documentación vive en `docs/`. En la raíz solo quedan `README.md` y los
punteros `AGENTS.md` / `CLAUDE.md`. Índice completo: `docs/00_INDICE.md`.

`docs/` quedó **mínimo y canónico** (los specs de origen numerados 01–07 se consolidaron
en estos y se eliminaron):

| Archivo (en `docs/`) | Qué es | Vigencia |
|---|---|---|
| **`AGENTS.md`** (este) | Estado actual + cómo trabajar (**punto de entrada**) | ✅ canónico |
| **`ESTADO_DEL_PROYECTO.md`** | Memoria del proyecto + casos de uso, reglas de negocio y gobernanza | ✅ |
| **`CHANGELOG.md`** | Historial de cambios | ✅ |
| **`DEPLOY_GRATIS.md`** | Despliegue Vercel+Render gratis | ✅ |
| **`ARQUITECTURA.md`** | Cómo está construido, en lenguaje normal (para no técnicos) | ✅ |
| **`ACUERDOS.md`** | Decisiones tomadas, motivo y coste de cambiarlas | ✅ |
| **`HISTORIA.md`** | De dónde viene el proyecto: línea del tiempo y changelog anterior al rebrand | ✅ |
| **`BRAND.md`** | **Fuente de verdad de la marca CallVeroQA** | ✅ canónico |
| **`DESIGN.md`** | Cómo se implementa `BRAND.md` en la app | ✅ |
| **`COMPLIANCE_CHECKLIST.md`** | Validaciones de Compliance/DPO/Seguridad previas a producción real | ✅ |
| **`RENOMBRADO_INFRA.md`** | Cómo renombrar repos/servicios/dominios a CallVeroQA (pendiente, lo hace el usuario) | ✅ |
| `00_INDICE.md` | Índice de la documentación | ✅ |
| `../README.md` (raíz) | Landing del repo | ✅ |

## 16. Dos repos: privado (completo) y público (limpio)

Hay **dos repositorios**:

- **`callveroqa` (completo)** — este repo, la **fuente de verdad**: código +
  `docs/` + `ops/` + prompts. Ponlo en **privado** en GitHub (Settings → Change visibility).
- **`callveroqa` (público, limpio)** — copia **derivada** que parece hecha a mano: solo código
  funcional (incluidos los prompts) + un `README.md` curado. **Sin** `docs/`, `AGENTS.md`,
  `CLAUDE.md`, READMEs de backend/frontend ni `ops/`; **historial propio** (autor
  `JBenjaminGM`, sin `Co-Authored-By`). Vive en `C:\Users\master\dev\callveroqa` en local.

**Publicar (regenerar el repo limpio):**

1. Commitea y `git push origin main` en el repo privado (como siempre).
2. Ejecuta `powershell C:\Users\master\dev\callveroqa\ops\publish-clean.ps1 -Message "<msg>"`
   (la 1ª vez además `-RemoteUrl "https://github.com/JBenjaminGM/callveroqa-public.git"`).

El script (`ops/publish-clean.ps1`, en **ASCII** — PS 5.1 rompe con UTF-8 sin BOM) espeja el
`main` commiteado, quita docs/`*.md`/`AGENTS`/`CLAUDE`/`ops`, escribe el README desde
`ops/clean-README.md`, commitea con historial limpio y hace push a `callveroqa`. No se edita el
repo limpio a mano; todo cambio nace en el privado y se republica.
