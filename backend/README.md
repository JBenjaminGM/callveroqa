# 🎧 CallVeroQA — Backend

Backend de la plataforma de Quality Assurance automatizado para call centers
bancarios del sector banca. Permite subir grabaciones de llamadas,
transcribirlas con IA y evaluarlas automáticamente contra una rúbrica dinámica
(7 dimensiones por defecto, con subcriterios activables).

> ⚠️ **No utilizar con datos reales de clientes sin la aprobación previa de
> Compliance.** (El header `X-Prototype-Notice` se conserva como salvaguarda interna.)

---

## 1. ¿Qué es esto?

Es una API REST construida con **Python + FastAPI** que:

1. Recibe archivos de audio (MP3, WAV, M4A, OGG, FLAC).
2. Los transcribe usando **Groq (Whisper large v3)**.
3. Enmascara la PII de la transcripción (best-effort).
4. Analiza la transcripción con **Groq (Llama 3.3 70B) por defecto**, con
   **Claude (Anthropic)**, **GPT (OpenAI)** o **Azure** como opciones, inyectando
   la **nota de producto** de la campaña en el prompt.
5. Devuelve scores por dimensión, un score global ponderado y recomendaciones.

El procesamiento pesado se hace en segundo plano con **Celery + Redis** en local;
en el despliegue gratis de Render corre **inline** (`PROCESS_INLINE=true`, vía
`BackgroundTasks`, sin worker). En ambos casos el frontend consulta el estado por
*polling*.

**Roles:** `admin` y `jefe` comparten permisos (gestión + analítica global);
`asesor` solo ve su propio rendimiento, su ficha y sus llamadas.

---

## 2. Requisitos previos

| Herramienta | Para qué | Descarga |
|---|---|---|
| Docker Desktop | Ejecutar todo el sistema localmente | https://www.docker.com/products/docker-desktop/ |
| Cuenta en Groq | Transcripción **y** análisis IA (proveedor por defecto, gratis) | https://console.groq.com |
| Cuenta en Anthropic / OpenAI | Solo si cambias el proveedor de análisis (opcional, de pago) | https://console.anthropic.com |

Con **Groq por defecto** (`AI_PROVIDER=groq`) una sola clave cubre transcripción
(Whisper large v3) y análisis (Llama 3.3 70B), y el coste de IA es **$0**.

No necesitas instalar Python ni PostgreSQL: Docker se encarga de todo.

---

## 3. Cómo obtener las API keys

### Groq (transcripción + análisis) — la única que necesitas

1. Entra a https://console.groq.com/ e inicia sesión.
2. Menú lateral → **API Keys** → **Create API Key**.
3. Copia la clave (empieza por `gsk_...`). **No se vuelve a mostrar.**

Con esta clave y `AI_PROVIDER=groq` ya tienes transcripción y análisis funcionando, gratis.

### Anthropic (opcional — solo si usas Claude para el análisis)

1. Entra a https://console.anthropic.com/ y crea una cuenta.
2. Añade un método de pago (solo se cobra el uso real, ~$0.02 por llamada).
3. **API Keys** → **Create Key**. Copia la clave (empieza por `sk-ant-...`).
4. Cambia `AI_PROVIDER=claude` en el `.env`.

### OpenAI (opcional)

Solo si quieres alternar a GPT (`AI_PROVIDER=openai`). https://platform.openai.com/api-keys

---

## 4. Configuración local (paso a paso)

```bash
# 1. Sitúate en la carpeta del proyecto
cd callveroqa/backend

# 2. Copia el archivo de ejemplo de variables de entorno
#    En Windows (PowerShell):  Copy-Item .env.example .env
cp .env.example .env

# 3. Edita .env y rellena al menos estas claves:
#    GROQ_API_KEY=gsk_...              # única clave imprescindible
#    AI_PROVIDER=groq                  # por defecto; gratis (Llama 3.3 70B)
#    JWT_SECRET=algo-largo-y-aleatorio
#    # ANTHROPIC_API_KEY=sk-ant-...    # opcional, solo si AI_PROVIDER=claude

# 4. Levanta todo el sistema (desde la raíz del repo)
docker compose up
```

Espera ~2 minutos. Cuando veas `Application startup complete`, abre:

- **http://localhost:8000/docs** → documentación interactiva de la API.

El arranque ejecuta automáticamente las migraciones y el *seed* de datos.

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

## 5. Cómo desplegar (gratis, $0)

El despliegue vigente es **Render** (backend) + **Vercel** (frontend), con coste
**$0**. La guía completa paso a paso está en **[`../docs/DEPLOY_GRATIS.md`](../docs/DEPLOY_GRATIS.md)**.
En vivo: API en https://callveroqa-api.onrender.com · frontend en https://callveroqa.vercel.app.

Resumen para el backend en Render (a partir del blueprint `render.yaml` de la raíz):

1. Sube este repositorio a GitHub.
2. En https://render.com → **New → Blueprint** y selecciona el repo (lee `render.yaml`).
3. Render aprovisiona el servicio web y, si aplica, la base de datos PostgreSQL.
4. Configura las variables de entorno del servicio:

   ```
   GROQ_API_KEY=gsk_...
   AI_PROVIDER=groq
   WHISPER_PROVIDER=groq
   PROCESS_INLINE=true            # procesa sin worker Celery (vía BackgroundTasks)
   # ANTHROPIC_API_KEY=sk-ant-... # solo si usas AI_PROVIDER=claude (de pago)
   JWT_SECRET=cadena-larga-aleatoria
   APP_ENV=production
   STORAGE_PROVIDER=local
   STORAGE_PATH=/data/audios
   CORS_ORIGINS=https://callveroqa.vercel.app
   ```

5. `DATABASE_URL` (y `REDIS_URL` si lo usas) los inyecta Render desde el blueprint.
6. La URL pública la asigna Render automáticamente; verifica en `https://callveroqa-api.onrender.com/docs`.
7. Carga los datos iniciales (admin, jefe, asesores, rúbrica, campañas, ejecutivos)
   ejecutando `python scripts/seed_data.py` desde la shell de Render, o deja que el
   comando de arranque lo haga.

> En el plan gratuito de Render el procesamiento corre dentro del mismo servicio
> (`PROCESS_INLINE=true`, sin worker Celery separado), y el backend se duerme tras
> ~15 min de inactividad (arranque en frío ~50 s). Para los detalles exactos del
> cold-start y su mitigación, sigue `../docs/DEPLOY_GRATIS.md`.

---

## 6. Estructura del proyecto

```
backend/
├── app/
│   ├── main.py            # Arranque de FastAPI, CORS, logging, routers
│   ├── config.py          # Configuración leída de variables de entorno
│   ├── database.py        # Conexión a PostgreSQL
│   ├── dependencies.py    # Autenticación JWT + require_manager (roles)
│   ├── limiter.py         # Rate limiting compartido
│   ├── models/            # Tablas de la base de datos (SQLAlchemy)
│   ├── schemas/           # Validación de entrada/salida (Pydantic)
│   ├── routers/           # Endpoints de la API
│   ├── services/          # Lógica de negocio (IA, storage, PDF, campañas, etc.)
│   ├── tasks/             # Tareas Celery (procesamiento asíncrono)
│   ├── prompts/           # Prompts para los modelos de lenguaje
│   └── utils/             # Seguridad y validación de audio
├── alembic/               # Migraciones de la base de datos (0001 → 0006)
├── scripts/seed_data.py   # Datos iniciales (usuarios, rúbrica, campañas, ejecutivos)
├── tests/                 # Tests automatizados
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 7. Endpoints principales

Prefijo `/api/v1`. Todos requieren JWT (`Authorization: Bearer <token>`) salvo
`POST /auth/login`. `[manager]` = solo `admin`/`jefe`; `[scoped]` = el asesor solo
accede a lo suyo.

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Iniciar sesión, obtener token JWT (rate limit 5/15min) |
| GET | `/auth/me` | Datos del usuario (incluye `role` y `agent_id`) |
| GET / POST | `/agents` | Listar `[scoped]` / crear `[manager]` ejecutivos |
| POST | `/agents/{id}/login` | Crear el login del asesor y vincularlo `[manager]` |
| PUT / DELETE | `/agents/{id}` | Editar / desactivar ejecutivo `[manager]` |
| GET / POST | `/campaigns` | Listar / crear campañas (nota de producto) |
| GET / PUT / DELETE | `/campaigns/{id}` | Detalle / editar / borrar campaña |
| POST | `/campaigns/extract` | Parsear un PDF de oferta y autocompletar la nota |
| POST | `/campaigns/assist` | Asistente IA para redactar la nota de producto |
| POST | `/calls` | Subir un audio para análisis |
| POST | `/calls/batch` | Subir varios audios `[manager]` |
| GET | `/calls` | Listado paginado `[scoped]` |
| GET | `/calls/{id}` | Detalle (transcripción + análisis) `[scoped]` |
| GET | `/calls/{id}/status` | Estado del procesamiento (polling) |
| PUT | `/calls/{id}/assign` | Asignar la llamada a un ejecutivo `[manager]` |
| POST | `/calls/{id}/retry` | Reintentar una llamada con error `[manager]` |
| GET | `/calls/{id}/report.pdf` | Descargar reporte PDF `[scoped]` |
| DELETE | `/calls/{id}` | Eliminar llamada `[manager]` |
| GET | `/dashboard/summary` | KPIs agregados (filtros campaña/agente/fechas) `[manager]` |
| GET | `/dashboard/campaigns` | KPIs por campaña `[manager]` |
| GET | `/dashboard/agents/{id}` | Performance de un ejecutivo `[scoped]` |
| GET / PUT | `/config/rubric` | Consultar / ajustar la rúbrica (PUT `[manager]`) |
| GET / PUT | `/config/settings` | Idioma + umbrales QA (PUT `[manager]`) |

El asesor recibe `403` al intentar el dashboard global, subir/asignar/reintentar/
eliminar llamadas, los settings o la gestión de ejecutivos.

---

## 8. Ejecutar los tests

El proyecto tiene **78 tests** automatizados (incluye la analítica de Fase 2:
métricas de conversación, compliance de nota de producto y endpoints de dashboard con scoping).

```bash
# Dentro del contenedor de la API
docker compose run --rm api pytest -q

# O en local, con un entorno virtual de Python:
pip install -r requirements.txt
pytest -q
#   En Windows con el venv del repo:  .venv\Scripts\python -m pytest -q
```

Los tests usan SQLite en memoria y mockean los servicios externos (no necesitan
PostgreSQL ni claves de API). Cubren auth, roles y scoping (admin/jefe/asesor),
ejecutivos, campañas, cálculo de score, enmascarado, matching difuso, idempotencia
del reintento, modo inline, umbrales QA y creación del login de asesor.

---

## 9. Solución de problemas comunes

| Problema | Solución |
|---|---|
| `docker compose up` falla al construir | Verifica que Docker Desktop esté corriendo. |
| La llamada se queda en `TRANSCRIBING` | En local revisa que el servicio `worker` esté activo y que `GROQ_API_KEY` sea válida; en Render basta `PROCESS_INLINE=true`. |
| `Invalid API key` de Anthropic | Solo aplica si `AI_PROVIDER=claude`: la clave debe empezar por `sk-ant-` y tu cuenta debe tener saldo. Con el `groq` por defecto no necesitas esta clave. |
| Error de CORS desde el frontend | Añade la URL exacta del frontend a `CORS_ORIGINS` (sin barra final). |
| El audio no se sube | Verifica formato (MP3/WAV/M4A/OGG/FLAC) y tamaño (≤ 100 MB). |

---

## 10. Notas sobre portabilidad

El código está preparado para migrar a infraestructura Azure sin reescribirse:

- Los proveedores de IA y transcripción usan **patrón factory**: basta cambiar
  las variables `AI_PROVIDER` / `WHISPER_PROVIDER`. El análisis admite
  **Groq (por defecto)**, Claude, OpenAI y Azure OpenAI; la transcripción admite
  **Groq (por defecto)** y Azure Speech.
- Toda la configuración vive en variables de entorno.
- Cada respuesta incluye el header `X-Prototype-Notice` (valor
  `"Evaluation environment - Do not use with real customer data"`) y los logs
  llevan el campo `environment: evaluation` para auditoría.
