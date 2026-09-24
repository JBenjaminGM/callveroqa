# 📚 Índice de documentación — CallVeroQA

> Toda la documentación del proyecto vive en esta carpeta **`docs/`**. Este es el
> punto de entrada. En la raíz del repo solo quedan `README.md` y los punteros
> `AGENTS.md` / `CLAUDE.md` (para que las IAs los descubran y apunten aquí).

**CallVeroQA** — *Calidad verificada en cada llamada.* Plataforma de QA
automatizado para call centers del sector banca. Desplegada en vivo:

- 🌐 Frontend: https://callveroqa.vercel.app · Backend: https://callveroqa-api.onrender.com
- 👤 Cuentas sembradas: `admin@callveroqa.com`, `jefe@callveroqa.com` y un asesor por ejecutivo demo. **Las contraseñas se generan al azar y se imprimen una vez** (`docker compose logs api`).

> Dos repos: **`callveroqa`** (completo, fuente de verdad — este) y **`callveroqa-public`**
> (público, solo código limpio). Ver `AGENTS.md` §16.

---

## ¿Qué leo según lo que quiero hacer?

| Quiero… | Lee |
|---|---|
| **Retomar el trabajo en un chat nuevo** | **`CONTINUAR.md`** ⭐ (empieza aquí) |
| **Entender cómo está construido** (sin saber programar) | **`ARQUITECTURA.md`** ⭐ |
| **Entender y modificar el código** (dev o IA) | **`AGENTS.md`** ⭐ (empieza aquí) |
| Ver qué decidimos y qué costaría cambiarlo | `ACUERDOS.md` |
| Ver de dónde viene el proyecto, en orden y en lenguaje normal | `HISTORIA.md` |
| Ver quién más resuelve esto, qué nos falta y qué viene después | `COMPETENCIA.md` |
| Ver qué falta para vender y en qué orden | `PLAN_PRODUCCION.md` |
| Ver el estado actual, casos de uso, reglas de negocio y lo pendiente | `ESTADO_DEL_PROYECTO.md` |
| Ver el historial de cambios | `CHANGELOG.md` |
| **Publicar / desplegar gratis** | `DEPLOY_GRATIS.md` |
| **Identidad de marca** (color, tipografía, tono) | **`BRAND.md`** ⭐ |
| Sistema de diseño e implementación | `DESIGN.md` |
| Validaciones legales previas a producción real | `COMPLIANCE_CHECKLIST.md` |
| Renombrar servicios, repos y dominios | `RENOMBRADO_INFRA.md` |

---

## Todos los documentos (vigentes)

- **`CONTINUAR.md`** — **Traspaso entre sesiones**: dónde estamos, qué sigue, cómo
  verificar que todo funciona y qué te hará perder tiempo si no lo sabes. Es lo primero
  que debe leer quien retome el proyecto.
- **`ARQUITECTURA.md`** — **Cómo está construida la aplicación, en lenguaje normal**: las dos
  mitades, el viaje de una llamada, dónde vive cada pieza y por qué, y un glosario de ocho
  palabras. Pensado para leerse sin saber programar.
- **`ACUERDOS.md`** — Las decisiones tomadas, el motivo de cada una y **qué costaría
  cambiarla**. Ninguna es inamovible; este documento existe para poder revisarlas con
  criterio. Incluye las decisiones aún abiertas.
- **`HISTORIA.md`** — De dónde viene el proyecto: la línea del tiempo y el registro de cambios anterior al rebrand.
- **`PLAN_PRODUCCION.md`** — Qué falta para que un cliente pague por esto: bloqueantes, confianza, producto y lo que no es código (gasto y cuentas externas). Dice qué está hecho y qué no.
- **`COMPETENCIA.md`** — Comparativa con Observe.AI, CallMiner, Zendesk QA y otras: qué pide el mercado, dónde destacamos, qué se ha cerrado y el plan siguiente.
- **`AGENTS.md`** — **Guía maestra de desarrollo / orientación para IAs**: estado
  actual, arquitectura, mapa del repo, cómo correr/testear/desplegar, *gotchas* y cómo
  hacer cambios. **El más importante; el punto de entrada de un chat nuevo.**
- **`ESTADO_DEL_PROYECTO.md`** — Memoria del proyecto: qué se construyó, casos de uso,
  reglas de negocio, gobernanza/compliance y qué queda.
- **`CHANGELOG.md`** — Historial de cambios (con commits).
- **`DEPLOY_GRATIS.md`** — Despliegue gratis paso a paso (Vercel + Render).
- **`BRAND.md`** — **Fuente de verdad de la marca CallVeroQA**: paleta (paper/ink
  con acentos rust y gold), tipografías Manrope/Inter/IBM Plex Mono, wordmark, formas
  y tono de voz. Cualquier cambio visual empieza aquí.
- **`DESIGN.md`** — Cómo se implementa `BRAND.md` en la app: tokens, componentes y
  dataviz. *La implementación canónica del color es `frontend/app/globals.css` +
  `tailwind.config.ts`.*
- **`COMPLIANCE_CHECKLIST.md`** — Comprobaciones de Compliance, DPO y Seguridad que
  deben cerrarse antes de tratar grabaciones reales de clientes.
- **`RENOMBRADO_INFRA.md`** — Pasos para alinear la infraestructura (repos de GitHub,
  servicios de Render, proyecto de Vercel) con el nombre nuevo, y por qué no se hizo
  automáticamente. Incluye cómo actualizar la `GROQ_API_KEY` en Render.

> Los specs de origen numerados (`01`–`07`) y la guía de Railway se **consolidaron**
> en los docs canónicos de arriba y se eliminaron para mantener `docs/` mínimo y
> coherente. El nombre anterior del producto, las identidades visuales anteriores,
> Railway y el lenguaje de "vista previa/prototipo" están **obsoletos**: qué fueron
> exactamente se cuenta en `HISTORIA.md`, y solo ahí.
>
> La presentación `CallQA_AI_Presentacion.pptx` se **eliminó**: reflejaba la marca
> anterior e incluía las credenciales demo antiguas.

---

> **Nota:** las rutas a código (`backend/...`, `frontend/...`) son relativas a la
> **raíz del repositorio**.
