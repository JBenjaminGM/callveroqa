# 🎧 CallVeroQA

**Calidad verificada en cada llamada.** Plataforma de Quality Assurance
automatizado para call centers del sector banca. Monorepo: backend + frontend +
documentación.

> ⚠️ **No utilizar con datos reales de clientes sin la aprobación previa de
> Compliance.** (El banner visible de "vista previa" se retiró de la UI; se conserva
> la salvaguarda interna `X-Prototype-Notice`.)

- 🌐 **En vivo:** https://callveroqa.vercel.app · API: https://callveroqa-api.onrender.com
- 👀 **Demo sin instalar nada:** `demo@callveroqa.com` / `CallVeroQA-Demo-2026` (solo lectura, con 90 días de datos ya cargados).
- 👤 **Cuentas de trabajo:** el seed crea `admin@callveroqa.com`, `jefe@callveroqa.com` y un asesor por cada ejecutivo demo. **Las contraseñas se generan al azar y se imprimen una sola vez**: léelas con `docker compose logs api`.
- 🎨 **Identidad de marca:** **[`docs/BRAND.md`](docs/BRAND.md)** (fuente de verdad del color, tipografía y tono).
- 🤖 **¿Eres una IA o un dev nuevo?** → **[`docs/AGENTS.md`](docs/AGENTS.md)** (guía completa).
- 📚 **Toda la documentación está en [`docs/`](docs/)** (índice: [`docs/00_INDICE.md`](docs/00_INDICE.md)).

![Panel del jefe de campaña](capturas/01-dashboard.png)

![Transcripción sincronizada con el audio](capturas/03-llamada.png)

---

## 🚀 Arranque rápido (Local)

Requisito: **Docker Desktop** abierto + una **API key de Groq** (gratis) en `backend/.env`.

```bash
cd callveroqa
docker compose up --build
```
- 🖥️ App: <http://localhost:3000>  ·  📚 API: <http://localhost:8000/docs>  ·  Detener: `docker compose down`.

### Activar la IA (gratis, $0)
En `backend/.env` basta una clave de **Groq** (hace transcripción **y** análisis):
```
GROQ_API_KEY=gsk_...
AI_PROVIDER=groq
WHISPER_PROVIDER=groq
```
> Claude / OpenAI / Azure son opcionales (de pago): cambia `AI_PROVIDER` y pon su API key.

---

## ✨ Qué hace

Sube audios → transcribe (Groq Whisper large v3) → enmascara PII (best-effort) →
analiza con LLM (Groq Llama 3.3 70B) contra una **rúbrica dinámica** → scores por
dimensión + score global ponderado + recomendaciones accionables + **reporte PDF**.

- **Roles:** `admin` y `jefe` (mismos permisos: gestión + analítica global) y
  `asesor` (solo su propio rendimiento, su ficha y sus llamadas).
- **Campañas con nota de producto:** cada campaña lleva una ficha de oferta (9
  campos) que la IA usa para evaluar si el ejecutivo ofreció lo correcto. Se crea
  por formulario, con asistente IA, o subiendo un PDF que la IA parsea.
- **Umbrales QA configurables:** objetivo, alertas de asesor/llamada y ranking,
  editables por el jefe.
- **Reproductor sincronizado:** el audio de la llamada se reproduce junto a la
  transcripción; al hacer clic en un segmento, el audio salta a ese momento.
- **Exportación CSV** del reporte del equipo, con los filtros del dashboard.
- **Identidad CallVeroQA:** paleta paper + ink con acentos rust y gold,
  tipografías Manrope / Inter / IBM Plex Mono. Ver **[`docs/BRAND.md`](docs/BRAND.md)**.

---

## 📂 Estructura

| Carpeta / archivo | Contenido |
|---|---|
| `backend/` | API FastAPI (+ worker Celery en local) — Python |
| `frontend/` | App web Next.js 14 (TypeScript) |
| **`docs/`** | **Toda la documentación** (guía `AGENTS.md`, estado, changelog, despliegue, diseño, pitch…) |
| `docker-compose.yml` · `render.yaml` | Config: stack local / blueprint de Render |

> El renombrado es total: repositorio, servicios, base local y claves de navegador usan
> `callveroqa`. Lo único que conserva los nombres anteriores es el mapa de migración de
> cuentas del seed, para no duplicar usuarios ya creados. Ver `docs/ACUERDOS.md`.

---

## 🛠️ Desarrollo y despliegue

- **Tests backend (147):** `cd backend && .venv\Scripts\python -m pytest -q`.
- **Frontend en local:** `cd frontend && npm install && npm run dev`.
- **Desplegar:** `git push origin main` → Vercel y Render redepliegan solos. Guía: **[`docs/DEPLOY_GRATIS.md`](docs/DEPLOY_GRATIS.md)**.

Para el detalle completo del estado y cómo trabajar, lee **[`docs/AGENTS.md`](docs/AGENTS.md)**.
