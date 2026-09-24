# CLAUDE.md

**Para empezar a codear en un chat nuevo:** (1) lee **[`docs/AGENTS.md`](docs/AGENTS.md)**
(guía completa: estado, arquitectura, mapa del repo, correr/testear/desplegar, *gotchas*);
(2) tu **memoria de proyecto** se carga sola (índice `MEMORY.md`). Docs en **[`docs/`](docs/)**.

El producto se llama **CallVeroQA** ("Calidad verificada en cada llamada").

Estado: plataforma **funcional y desplegada**, y **terminada** (el banner de
"prototipo/vista previa" se **retiró** de la UI; solo queda el header interno
`X-Prototype-Notice`). Además de la analítica y el reproductor sincronizado, ya
**calibra**: revisión humana que **no pisa la nota de la IA**, sesión de puntuación a
ciegas y panel de acuerdo IA-humano (`/calibracion`); y **cierra el ciclo**: el asesor
responde a su evaluación y puede pedir revisión, y el panel del jefe abre con «a quién
escuchar hoy y por qué». El traspaso entre sesiones vive en **`docs/CONTINUAR.md`**.

Esenciales:
- **IA = Groq por defecto** (`AI_PROVIDER=groq`): Whisper large v3 + Llama 3.3 70B, gratis.
  Factory portable a Claude/OpenAI/Azure. **El proveedor lo fija la env var, nunca la BD.**
- **Procesamiento:** Celery+Redis en local (`docker compose`); **inline**
  (`PROCESS_INLINE=true`, sin worker) en Render. **Despliegue vigente = Render + Vercel**
  (Railway es HISTÓRICO: cualquier mención a Railway en comentarios/ejemplos es deuda, no el estado real).
- **Roles:** `admin`/`jefe` (gestión + analítica global) y `asesor` (solo su rendimiento).
  `is_manager` / `require_manager` protegen lo de gestión.
- **Campañas con nota de producto:** entidad `Campaign` (9 campos); se inyecta en el prompt.
- **Trabajar en `C:\Users\master\dev\callveroqa`** (NO la copia de OneDrive).
- **Tests:** desde `backend/`, `.\.venv\Scripts\python.exe -m pytest -q` (147 tests). Migraciones 0001–0011.
- **Desplegar:** `git push origin main` → Vercel + Render redepliegan solos. **`GROQ_API_KEY`
  en prod vive en el dashboard de Render (`sync: false`), no en el repo.**
- **Dos repos:** privado `callveroqa` (completo) + público `callveroqa` (código limpio). Publicar
  el limpio: `ops/publish-clean.ps1` (ver AGENTS §16).
- **Seed sin contraseñas fijas:** se generan al azar y se imprimen una vez
  (`docker compose logs api`); fijables con `SEED_ADMIN_PASSWORD` / `SEED_JEFE_PASSWORD` /
  `SEED_ASESOR_PASSWORD`. Cuentas: `admin@callveroqa.com`, `jefe@callveroqa.com`.
- **Diseño = identidad CallVeroQA.** Fuente de verdad de la marca: **`docs/BRAND.md`**
  (paper + ink, acentos rust y gold; Manrope / Inter / IBM Plex Mono; radios 8/6 px).
  Implementación canónica del color: `frontend/app/globals.css` + `tailwind.config.ts`.
  **Las identidades visuales anteriores están OBSOLETAS**: cuáles fueron y qué
  colores, tipografías y clases traían está en `docs/HISTORIA.md`. Si encuentras
  algo de eso en el código, es deuda; corrígelo contra `BRAND.md`.
- **Infra renombrada** (septiembre 2026): Render sirve `callveroqa-api` +
  `callveroqa-db`. Se pudo hacer sin migrar nada porque la PostgreSQL del plan
  gratuito **había caducado** y los datos de producción ya se habían perdido.
- **Renombrado total:** no queda ningún identificador con la marca anterior. Los
  únicos restos vivos son los mapas de migración de emails del seed (`@callaibrate.com`,
  `@callqa.com` → `@callveroqa.com`), que deben quedarse.
