# Historia

> De dónde viene CallVeroQA (antes CallAIbrate, y antes CallQA AI): qué pasó, en
> qué orden, y qué se cambió antes de cada rebrand.
>
> **Este es el único documento del repositorio donde aparecen los nombres anteriores
> del producto y la identidad visual anterior** (salvo los identificadores técnicos
> que los conservan a propósito, listados en `ACUERDOS.md` A-01). Se nombran porque así era
> entonces. Reescribirlos dejaría frases falsas —«identidad de marca X en toda la
> app» nunca fue mentira cuando se escribió— y borrarlos dejaría la historia sin
> sentido. Nada de lo que hay aquí es estado actual: para eso están
> [`ESTADO_DEL_PROYECTO.md`](ESTADO_DEL_PROYECTO.md) y
> [`CONTINUAR.md`](CONTINUAR.md).

---


## Junio 2026 · Construcción

| Cuándo | Qué pasó |
|---|---|
| **1 jun** | **Nace el proyecto.** En un solo día se levanta todo: backend, frontend, base de datos y las primeras pruebas. Ese mismo día se decide que la IA sea Groq (gratis) y se despliega por primera vez en internet. |
| **3 jun** | Se ordena la documentación en la carpeta `docs/`. |
| **13 jun** | **Campañas.** Cada campaña pasa a tener una "nota de producto" (qué se vende, a qué precio, qué frases son obligatorias) y la IA evalúa si el ejecutivo la respetó. |
| **16 jun** | ⚠️ **Se sube por error una clave de Groq real al repositorio.** Se detecta y se revoca una semana después. |
| **22 jun** | **Roles.** Aparecen tres perfiles: administrador, jefe y asesor. Cada uno ve solo lo que le corresponde. |
| **23 jun** | **Fase 2: analítica.** Alertas, KPIs por campaña, percentil del asesor, métricas de cómo se habla en la llamada. Y un rediseño completo de los indicadores. |

## Julio 2026 · Orden

| Cuándo | Qué pasó |
|---|---|
| **10-11 jul** | Se monta el sistema de dos repositorios: uno privado con todo, otro público solo con el código limpio. |
| **11 jul** | Auditoría de coherencia: se borra código muerto y se corrige documentación desactualizada. **Último cambio antes de dos meses de silencio.** |

## Agosto 2026 · La caída silenciosa

| Cuándo | Qué pasó |
|---|---|
| *(sin fecha exacta)* | ⚠️ **La base de datos de producción caduca y Render la elimina.** El plan gratuito las borra a los 30 días. El backend queda muerto: arranca, no encuentra la base y se apaga. **Nadie se entera durante dos meses**, porque el vigilante que hacía ping estaba mal configurado y se tragaba el error. Los datos de producción se pierden. No había copia de seguridad. |

## Septiembre 2026 · Rebrand y reconstrucción

| Cuándo | Qué pasó |
|---|---|
| **7 sep** | **El proyecto pasa de "CallQA AI" a "CallAIbrate".** Identidad nueva completa: paleta, tipografías, wordmark. Se retira la marca Minsait. |
| **7 sep** | **Reproductor de audio sincronizado**: se escucha la llamada mientras se resalta la frase que suena; al hacer clic en un segmento, el audio salta ahí. |
| **7 sep** | **Exportación a CSV** del reporte del equipo. |
| **7 sep** | **Seguridad:** las contraseñas de demostración dejan de estar escritas en el código; ahora se generan al azar. Se añade un seguro que impide arrancar en producción con la clave de firma de ejemplo. |
| **8 sep** | **Se descubre la caída.** Se reconstruye la infraestructura desde cero, aprovechando para renombrarla toda a `callaibrate`. Se pierde lo que había; no había nada que recuperar. |
| **8 sep** | **Se arregla un bug que expulsaba al usuario:** recargar cualquier página te devolvía al login. |
| **8 sep** | **Vigilancia real y copias de seguridad:** el ping ahora falla y avisa; se añade un volcado diario de la base de datos. |
| **8 sep** | ⚠️ **Groq retira el acceso al modelo de análisis.** Se cambia a `openai/gpt-oss-120b` y se verifica de punta a punta con una llamada real. |
| **9 sep** | Documentación de arquitectura, esta línea del tiempo y el registro de acuerdos. |
| **9 sep** | **La demo existe.** 67 llamadas de ejemplo con seis grabaciones reales y tendencias intencionadas, más una cuenta pública de solo lectura. Hasta entonces quien abría el enlace veía un panel vacío. |
| **9 sep** | **Se quitan las fricciones** que se notaban en los primeros minutos: los pesos de la rúbrica se reajustan solos, la lista de llamadas se refresca sola y aparecen las acciones en lote. |
| **9 sep** | **El producto empieza a calibrar.** Hasta aquí la IA puntuaba y su palabra era definitiva. Ahora una persona puede revisar la nota —sin pisar la de la IA—, puntuar a ciegas y ver en qué criterios discrepan más. Es lo que da sentido al nombre. |
| **9 sep** | **Se cierra el ciclo.** El asesor puede responder a su evaluación y pedir revisión; el panel del jefe abre con «a quién escuchar hoy y por qué» en vez de con medias. |
| **11 sep** | **Pasada de diseño.** Dos revisiones con skills de terceros sobre la interfaz ya terminada. Aparecen dos cosas que llevaban ahí desde el principio y nadie había visto: no existía una capa de tokens de movimiento —cada componente inventaba su duración— y **ningún botón de la aplicación respondía al pulsarlo**. Se corrigen esas y doce cosas más, ninguna de lógica. |
| **21 sep** | **El producto pasa de "CallAIbrate" a "CallVeroQA".** *CallAIbrate* obligaba a explicar el juego de palabras; *CallVeroQA* (Call · Vero · QA) se entiende a la primera. Tagline nuevo: «Calidad verificada en cada llamada». Solo cambian nombre, wordmark y copy: paleta, tipografía y símbolo se quedan. La infraestructura desplegada conserva por ahora el nombre `callaibrate`. |

---

## Las tres lecciones que costaron caro

1. **Un servicio "gratis" puede borrarte los datos.** El plan gratuito de Render caduca las
   bases PostgreSQL a los 30 días. Volverá a pasar si nada cambia.
2. **Un vigilante que nunca falla no vigila nada.** El ping terminaba en `|| true`: siempre
   daba verde. Por eso dos meses de caída pasaron desapercibidos.
3. **Un proveedor de IA puede quitarte un modelo sin avisar**, aunque su documentación siga
   listándolo. Conviene poder cambiar de proveedor con una variable — y eso ya está resuelto.

---

---

# Registro de cambios anterior al rebrand

> Movidas **tal cual** desde [`CHANGELOG.md`](CHANGELOG.md), sin tocar una coma.
> El changelog vigente arranca en CallAIbrate; todo lo de aquí abajo es de antes.
> Lo más nuevo, arriba.

## Auditoría de coherencia y limpieza
- `Código muerto eliminado`: componente `kpi-card.tsx` (sustituido por `StatCard`),
  factory `require_role` sin uso, fixture `seed_rubric`, campo `estimated_completion_seconds`,
  y los settings `ai_provider`/`whisper_provider` que se persistían en BD pero **nunca se
  leían** (el proveedor lo fija la env var). Artefactos legacy de Railway (`railway.json`,
  `Procfile`).
- `Comentarios/docstrings alineados al estado real`: Railway→Render, "MVP"→"por defecto",
  3→4 proveedores de IA, Celery→dual (inline), NPS→ranking, `environment="evaluation"`,
  y limpieza de estética obsoleta en el frontend (Aetheric/Índigo/"immersive"/`backdrop-blur`
  muerto sobre superficies sólidas). Color del PDF `#E84F7A`→Pruno `#480e2a`.
- `Docs consolidados`: se eliminaron los specs de origen numerados (01–07); su contenido
  útil (casos de uso, reglas de negocio, gobernanza/compliance) se consolidó en
  `ESTADO_DEL_PROYECTO.md`. `docs/` queda mínimo y coherente.
- `Migración 0007`: `server_default` de `users.role` corregido de `'supervisor'` (legacy) a `'jefe'`.
- `.env.example` completado (`PROCESS_INLINE`, CORS, id de modelo Claude) y `.env.local.example`
  apuntando a Render.

## Rediseño premium de indicadores y UX
- `Sistema de dataviz de marca` (`frontend/components/dashboard/viz.tsx`): **ScoreGauge**
  (anillo de score), **Sparkline**, **Donut**, **MiniProgress**, **DeltaPill** y
  **BrandTooltip**; **StatCard** (KPI con delta + sparkline + progreso a meta),
  **SectionHeader/Eyebrow** y **CallsTrendChart** (área con gradiente + línea de meta).
- `Dashboard del jefe rediseñado`: toolbar compacto con **control segmentado** de
  periodo, banda de resumen con **gauge héroe** + StatCards, tendencias (área + **donut**
  de distribución), **tabla de campañas** con barras inline y delta chips, **alertas con
  franja de severidad** e iconos por tipo, rankings y dinámica de conversación.
  `/mi-panel` (percentil con barra de posición) y `calls/[id]` (gauge de score) alineados.
  Todo fiel a la identidad Minsait (paleta, chaflanes, titulares en minúscula, ForFuture Sans).
- `Banner de prototipo eliminado` de la UI (layout + login). El header HTTP
  `X-Prototype-Notice` se conserva.

> 🔑 **Nota de operación:** la IA en producción depende de `GROQ_API_KEY` en **Render**
> (`sync: false`, se pone a mano en el dashboard). Si Groq devuelve `401`, actualízala con
> la key válida; `git push` no la cambia.

## Fase 2 — Analítica de alto impacto
- `Dashboard del jefe`: fila de **alertas accionables** (asesor bajo umbral, caída de
  tendencia, llamadas en banda roja, claim prohibido / frases obligatorias omitidas,
  anomalía de sentimiento), **KPIs por campaña** con delta vs periodo previo (% rojas,
  sentimiento, duración, volumen), **radar de dimensiones del equipo** y **top problemas
  recurrentes** (agregación de `Analysis.recommendations`).
- `Métricas de conversación` deterministas ($0) desde `Transcription.segments`:
  talk-to-listen ratio, % de silencio/dead-air, monólogo más largo del agente,
  palabras/min y turnos/min. Servicio `conversation_metrics_service.py`, columna
  `Call.conversation_metrics` (**migración 0006**), cálculo en el pipeline y **al vuelo**
  para llamadas antiguas. Se exponen en el detalle de llamada y agregadas en el dashboard.
- `Vista asesor (/mi-panel)`: **percentil anónimo** dentro de su campaña (oculto bajo
  `qa_min_calls_ranking`), **"qué cambiar"** (recomendaciones agregadas por dimensión con
  evidencia de un segmento real) y **desglose por campaña** con cumplimiento de la nota de
  producto (cobertura de frases obligatorias, claims prohibidos).
- `Endpoints nuevos` bajo `/dashboard`: `/by-campaign`, `/alerts`, `/top-recommendations`
  (todos `[manager]`), `/agents/{id}/percentile` y `/agents/{id}/recommendations` (`[scoped]`).
  `/summary` extendido con `team_dimension_averages`, `avg_duration_seconds`,
  `red_call_count`/`red_call_pct` y `conversation_summary`.
- `Compliance de nota de producto` (`compliance_service.py`): comprobación determinista
  best-effort de frases obligatorias y claims prohibidos contra lo que dijo el agente.
- `Frontend`: editor de **umbrales QA** en `/settings`, UI **"crear acceso de asesor"** en
  `agents/[id]` (`POST /agents/{id}/login`), métricas de conversación en `calls/[id]`.
  Componentes en `frontend/components/dashboard/insights.tsx`; hooks en `lib/queries.ts`.
- `Banner de prototipo eliminado`: se retira el banner "Vista previa / entorno de
  evaluación" de la UI (layout y login). El header HTTP `X-Prototype-Notice` se conserva.
- `Tests`: +17 (`backend/tests/test_dashboard_phase2.py`), total **78**.

## Fix cold-start (producción gratis)
- `Cold-start mitigado`: el plan gratis de Render duerme el backend tras ~15 min
  (arranque en frío ~50 s, que se veía como "error de API"). Se añade GitHub Action
  `.github/workflows/keepalive.yml` (ping a `/health` cada 12 min) + **resiliencia
  en `frontend/lib/api.ts`** (timeout 90 s, reintentos en cold start, mensaje
  "activando el servidor").

## Lenguaje "vista previa para evaluación"
- `Limpieza de lenguaje`: se elimina el de **"demo interna"**. El banner pasa a
  *"Vista previa — entorno de evaluación. No utilizar con datos reales de clientes
  sin la aprobación previa de Compliance"*; el header `X-Prototype-Notice` pasa a
  valer *"Evaluation environment - Do not use with real customer data"*; el log JSON
  usa `environment="evaluation"`; el PDF dice *"Vista previa para evaluación"*. El
  login **ya no muestra credenciales demo** y el seed **ya no imprime contraseñas**.

## Roles y umbrales QA
- `Roles admin/jefe/asesor`: tres roles — `admin` y `jefe` con los **mismos
  permisos** por ahora (gestión + analítica global, helper `is_manager`); `asesor`
  solo ve **su propio rendimiento**. `User.role` + `User.agent_id` (FK a agents);
  dependencia `require_manager`; `POST /agents/{id}/login` crea el login del asesor
  y vincula User↔Agent. Frontend: navegación/redirección por rol (asesor → `/mi-panel`,
  admin/jefe → `/dashboard`), guard por rol y página "Mi rendimiento". Migración
  `0005` (`users.agent_id` FK + backfill `'supervisor'`→`'jefe'`).
- `Umbrales QA configurables` en `/config/settings` (`qa_target_score=90`,
  `qa_low_agent_threshold=80`, `qa_red_call_threshold=60`, `qa_min_calls_ranking=5`,
  `qa_trend_drop_alert=5`), persistidos en `app_settings`, editables solo por manager.

## Rebrand a la identidad Minsait
- `Rebrand Minsait`: UI rebrandeada a la identidad oficial **Minsait** — paleta
  **Pruno `#480E2A`** + **Gris Cerámica `#E3E2DA`** dominantes, **Fucsia `#FF0054`**
  solo como acento; tipografía **ForFuture Sans** (woff2 locales), logo oficial,
  contenedores **achaflanados** (`.chamfer`), titulares en minúscula con la palabra
  clave en Fucsia, CTA en píldora, modo claro por defecto + sidebar siempre Pruno.
  Tokens en `frontend/app/globals.css` + `tailwind.config.ts`. **Sustituye** a
  "Aetheric Intelligence" / Índigo/Slate (obsoletos).

## Campañas con nota de producto
- `Campañas`: entidad `Campaign` (tabla `campaigns`) con una **nota de producto de
  9 campos** (producto/servicio, descripción de la oferta, beneficios, precio/condiciones,
  requisitos, frases obligatorias, claims prohibidos, público objetivo, notas). Se crea
  por formulario (con asistente IA) o subiendo un **PDF** que la IA parsea (pypdf + LLM)
  y autocompleta. La nota se **inyecta en el prompt de análisis** para evaluar si el
  ejecutivo ofreció la oferta correcta. `calls.campaign_id` (se conserva `campaign_type`
  por compatibilidad y filtros). Endpoints `/campaigns` CRUD + `/campaigns/extract` (PDF)
  + `/campaigns/assist` (IA). Dependencia nueva backend: **pypdf**. Módulo frontend
  `/campaigns`. Migración `0004` (tabla `campaigns` + `calls.campaign_id` + backfill).

## Despliegue en producción (gratis)
- **Publicado** en Vercel (frontend) + Render (backend + PostgreSQL), coste **$0**.
  Frontend: https://callqa-ai.vercel.app · Backend: https://callqa-api.onrender.com
- `Fix deploy Render`: el arranque (migraciones + seed + uvicorn) se movió al **CMD del
  Dockerfile** para evitar que Render partiera mal el comando con comillas (exit 127). (`53ee2d3`)
- `Despliegue gratis`: **procesamiento inline** (`PROCESS_INLINE`, vía `BackgroundTasks`)
  para correr **sin Celery/Redis** en el tier gratis; `render.yaml` (blueprint Render con
  PostgreSQL); normaliza `postgres://`→`postgresql://`; `DEPLOY_GRATIS.md`. (`8523b01`)

## Auditoría de consistencia
- `Consolidación de docs`: **toda la documentación se movió a `docs/`**; en la raíz solo
  quedan `README.md` y los punteros `AGENTS.md` / `CLAUDE.md`. (`2d10ab1`)
- `AGENTS/CHANGELOG/docs`: guía canónica `AGENTS.md`, este changelog y sincronización
  de la documentación de origen. (`d43940c`)
- `Docs sync`: toda la documentación a la realidad **"Groq por defecto"** (proveedor IA,
  costos $0, diarización por LLM, colores Índigo/Slate, rúbrica editable, tests). (`59152cf`)
- `Fixes funcionales/config`: `/config/settings` reporta el **proveedor REAL** (env, no BD);
  defaults a `groq`; `dimensionLabel` humaniza categorías nuevas. (`f077825`)

## Funcionalidades
- `Filtros del dashboard` (campaña, ejecutivo, rango de fechas, periodo) + endpoint
  `/dashboard/campaigns`. **Rediseño de paleta a Índigo/Slate** (en `globals.css`). (`c518519`)
- `Rúbrica con subcategorías`: activables + **añadir/eliminar categorías y subcategorías**;
  la IA las usa (prompt dinámico). Migración `0003` (`rubric_config.criteria`). (`d184f3c`)
- `Diarización por contenido (LLM)` en vez de la heurística de pausas (que queda de fallback);
  `max_tokens` 4000. (`21319bb`)
- `Botón Actualizar` en listado y detalle de llamadas. (`9a76dbf`)

## Correcciones
- `Dashboard 500` ("Network Error"): comparación de fechas naïve/aware → `datetime.utcnow()`. (`9a76dbf`)
- `Reintento idempotente`: `_run_pipeline` borra transcripción/análisis previos (evita
  `IntegrityError UNIQUE(call_id)`); `db.rollback()` antes de marcar `ERROR`. (`c61c3fb`)
- `Enmascarado endurecido`: cubre tarjetas con guiones/espacios y números dictados
  (best-effort, documentado). Claims de seguridad del README ejecutivo hechos honestos. (`c61c3fb`)

## Base
- `Initial commit`: backend FastAPI + Celery, frontend Next.js, docs. (`134b42c`)

---

## Cómo leer esto en el futuro

- **Esta historia** cuenta *de dónde venimos*. Nada de aquí es estado actual.
- **[`CHANGELOG.md`](CHANGELOG.md)** cuenta *qué se ha cambiado* desde el rebrand.
- **[`ACUERDOS.md`](ACUERDOS.md)** cuenta *qué decidimos y por qué*, y qué costaría cambiarlo.
- **[`ESTADO_DEL_PROYECTO.md`](ESTADO_DEL_PROYECTO.md)** cuenta *dónde estamos ahora*.
- **[`CONTINUAR.md`](CONTINUAR.md)** es el traspaso entre sesiones de trabajo.
