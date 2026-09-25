# CLAUDE.md

**Para empezar a codear en un chat nuevo, en este orden:**
1. **[`docs/CONTINUAR.md`](docs/CONTINUAR.md)** — el traspaso: dónde trabajar, cómo
   arrancar en local, estado exacto, **qué está bloqueado esperando al usuario** y los
   diez tropiezos que hacen perder tiempo.
2. **[`docs/PLAN_PRODUCCION.md`](docs/PLAN_PRODUCCION.md)** — qué falta para vender y en
   qué orden. **Es el documento que manda ahora.**
3. **[`docs/AGENTS.md`](docs/AGENTS.md)** — arquitectura, mapa del repo, cómo
   correr/testear/desplegar y los *gotchas*.

Tu **memoria de proyecto** se carga sola (índice `MEMORY.md`). Docs en **[`docs/`](docs/)**.

El producto se llama **CallVeroQA** ("Calidad verificada en cada llamada").

Estado: plataforma **funcional, desplegada y en camino de venderse**. Ya no es solo un
portafolio: el trabajo actual es cerrar lo que impide que un cliente pague por ella.
Además de la analítica y el reproductor sincronizado, **calibra** (revisión humana que no
pisa la nota de la IA, sesión a ciegas y panel de acuerdo en `/calibracion`), **cierra el
ciclo** (el asesor responde y puede pedir revisión; el panel abre con «a quién escuchar
hoy y por qué»), **justifica cada nota** (evidencia con saltos al audio y criterios
críticos que suspenden la llamada) y **dice por qué llaman los clientes** (motivos de
llamada). Tiene gestión de cuentas y contraseñas, retención de grabaciones y supresión de
datos de una persona.

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
- **Tests:** desde `backend/`, `.\.venv\Scripts\python.exe -m pytest -q` (209 tests). Migraciones 0001–0016.
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
- **URLs vivas (comprobado el 25 sep 2026):** `callaibrate-api.onrender.com` y
  `callaibrate.vercel.app`. Los nombres `callveroqa-api` / `callveroqa.vercel.app`
  **todavía no existen** (dan 404): renombrar los servicios está pendiente del usuario
  y preparado en la rama `infra/renombrar-servicios` (ver `docs/CONTINUAR.md`). La
  PostgreSQL del plan gratuito ya caducó una vez y se recreó; volverá a caducar.
- **Renombrado total:** no queda ningún identificador con la marca anterior. Los
  únicos restos vivos son los mapas de migración de emails del seed (`@callaibrate.com`,
  `@callqa.com` → `@callveroqa.com`), que deben quedarse.
