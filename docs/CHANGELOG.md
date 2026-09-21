# Changelog — CallVeroQA

Cambios relevantes. Formato: descripción (commit). Lo más nuevo arriba.

> Arranca en el rebrand a CallAIbrate (hoy CallVeroQA). Lo anterior está en
> [`HISTORIA.md`](HISTORIA.md), movido tal cual: nombra el producto y la identidad
> visual de entonces porque así era. Es historia, no estado.

## Rebrand: CallAIbrate → CallVeroQA

El nombre anterior obligaba a explicar el juego de palabras. **CallVeroQA** = *Call* ·
*Vero* (verdadero, verificado) · *QA*. Tagline: «Calidad verificada en cada llamada».
Paleta, tipografía y símbolo no cambian.

- `Wordmark`: `Call<Vero>QA`, con "Vero" en `rust` (antes "AI"). Login, sidebar,
  metadatos, PDF, título de la API y `/health` usan el nombre nuevo.
- `Cuentas sembradas`: `admin@` / `jefe@` / `demo@callveroqa.com`. El seed **renombra**
  las cuentas `@callaibrate.com` existentes (conservan contraseña e historial; la demo
  pública pasa a `CallVeroQA-Demo-2026`) en vez de duplicarlas.
- `Loggers` y app de Celery: `callveroqa.*`.
- **Sin tocar, a propósito:** servicios y URLs de Render/Vercel (`callaibrate-*`), el
  repositorio, la clave `callaibrate-theme` de localStorage (cambiarla resetea el tema de
  todos) y los identificadores `callqa` ya documentados. Ver `ACUERDOS.md` A-01.

## Pasada de diseño: capa de movimiento y suelo de calidad

Dos revisiones con skills de terceros, sobre el frontend ya terminado. Ninguna tocó
lógica: son 14 arreglos de interfaz.

**Movimiento** (skill de design engineering de Emil Kowalski):

- `Tokens de movimiento`: no existían. Cada componente escribía su duración y su curva
  (0.2s, 0.28s, 0.7s, 0.9s, `duration-200`). Ahora hay dos curvas y tres duraciones en
  `globals.css`, expuestas como utilidades en `tailwind.config.ts`.
- `:active` **no aparecía ni una vez en todo el frontend**: ningún botón respondía al
  pulsarlo. `.press-feedback` los baja a 0.97 en 160 ms.
- `transition: all` retirado de input, textarea y select — animaba también layout y paint.
- La **tarjeta deja de animarse sola**. Con quince por pantalla, el panel parpadeaba en
  cada visita; la entrada pasa al contenedor, donde sí cumple su propósito.
- El **anillo del score barre desde vacío en el primer pintado**. Tenía una transición,
  pero una transición no se dispara al montar: aparecía relleno la primera vez y solo se
  animaba al cambiar de filtro, justo al revés de lo útil.
- Gauge, donut y barras bajan de 700–900 ms a 450: se repiten en cada cambio de filtro.
- `hoverOnlyWhenSupported` en Tailwind mete los 13 `hover:` interactivos dentro de
  `(hover: hover) and (pointer: fine)`: dejan de dispararse al tocar en pantalla táctil.
- Las **pestañas de calibración** tienen subrayado deslizante; antes el color transicionaba
  pero la línea saltaba de sitio.
- La **revelación de la sesión a ciegas** entra escalonada y el remate —la diferencia—
  llega el último, cuando los anillos ya han barrido. Era un cambio instantáneo.
- `prefers-reduced-motion` retira desplazamiento y escala conservando opacidad y color,
  en vez de cubrir solo un fade.
- El spinner gira en 700 ms y no en 1 s: la espera parece más corta aunque el backend
  tarde lo mismo, que con un plan gratuito que despierta en ~50 s no es poco.

**Suelo de calidad** (skill IMPECCABLE, `pbakaus/impeccable`):

- `Tarjeta fantasma` resuelta: la tarjeta declaraba borde **y** sombra, dos sistemas de
  profundidad discutiendo. Se queda el borde, que es lo que pide un mundo paper+ink.
- `Tarjetas anidadas` retiradas: doce contenedores internos llevaban borde propio dentro
  de una tarjeta. El fondo ya los separa.
- `Bordes de color de más de 1px` (franja de severidad de 3 px, `border-l-4` del estado
  vacío, `border-l-2` del segmento activo y de la cita) reducidos a 1 px o eliminados
  cuando el icono o el fondo ya llevaban el color.
- `Glifos unicode como iconos`: `DeltaPill` usaba ↑ ↓ →, que heredan la métrica de la
  fuente y se alinean distinto en cada plataforma. Ahora son iconos de lucide, como el
  resto de la aplicación.
- `Superficies del navegador` tematizadas: `::selection`, `caret-color` y el desplazamiento
  del subrayado de los enlaces venían con los valores por defecto del navegador, que no
  pertenecen a ninguna identidad.

Un hallazgo de la skill **no** se aplicó: prohíbe el *eyebrow* sobre los titulares. Aquí
lo define `BRAND.md`, y la propia skill dice que el brief manda sobre sus reglas.

## Fase 3 — Cerrar el ciclo de coaching
- `El asesor responde`: tabla `acknowledgements` (**migración 0010**). Da la evaluación
  por leída, se explica y puede **pedir revisión**; el jefe contesta en el mismo
  registro y con eso la cierra. Lo firma **quien fue evaluado**: un jefe no puede acusar
  recibo en su nombre. Reabrir una petición borra la respuesta anterior, para que no pase
  por contestada sin que nadie haya leído lo nuevo.
- `A quién escuchar hoy` (`GET /coaching/who-to-listen`): el dashboard abre con esto en
  vez de con medias. Como mucho cinco llamadas, cada una con su motivo — petición de
  revisión abierta, banda roja sin escuchar, muy por debajo de la media del propio
  asesor, y asesor del que nadie ha escuchado nada. **Ordena por motivo, no por nota**:
  una roja siempre puntuará menos que una recurrida, y por nota colaría por delante de
  una persona esperando respuesta. Cada llamada aparece una sola vez.
- `Panel del asesor`: abre con las evaluaciones que tiene sin leer, antes que su promedio.
- `Subida de una carpeta entera` arrastrándola, a cualquier profundidad, más un botón
  «elegir una carpeta». `readEntries` devuelve los hijos por tandas y hay que insistir
  hasta que conteste vacío, o una carpeta con muchas grabaciones llega cortada.
- `Endpoints nuevos`: `/calls/{id}/acknowledgement` (GET/PUT), `/calls/{id}/acknowledgement/reply`,
  `/coaching/pending`, `/coaching/my-pending`, `/coaching/who-to-listen`.
- `Tests`: 113 → **127**.

## Fase 2 — Calibración: revisión humana y acuerdo IA-humano
- `Revisión humana`: tabla `reviews` (**migración 0009**). **La nota de la IA no se pisa**:
  son dos registros distintos sobre la misma llamada y el detalle muestra las dos con su
  diferencia. El global lo pondera el backend con la rúbrica —la misma fórmula que usa la
  IA— y **renormaliza** sobre los pesos presentes, para que una rúbrica cambiada después
  del análisis no hunda la nota.
- `Sesión a ciegas` (`/calibracion`): `GET /calibration/calls/{id}` devuelve audio y
  transcripción **sin el análisis**, así que el score no llega al navegador y la ceguera
  no depende de que la interfaz lo oculte. Al guardar se revela la comparación.
- `Panel de acuerdo` (`GET /calibration/agreement`): por dimensión, sesgo (humano − IA),
  desviación media absoluta y % de acuerdo dentro de ±5 puntos. **Ordena por desviación
  media, no por sesgo**: el sesgo se cancela entre llamadas y la desviación no, así que
  una dimensión puede tener sesgo cero y estar pésimamente calibrada. La peor se destaca
  con el enlace para reescribir la rúbrica.
- `Endpoints nuevos`: `/calls/{id}/review` (GET/PUT/DELETE), `/calibration/queue`,
  `/calibration/calls/{id}`, `/calibration/agreement`.
- `Rol`: lo hace el `jefe` que ya existía, sin roles nuevos. El asesor no entra a
  `/calibracion` pero sí ve la revisión de sus propias llamadas.
- `Tests`: 95 → **113**.

## Fase 1 — Quitar las fricciones de los primeros minutos
- `Pesos de la rúbrica relativos`: mueves uno y los demás se reajustan solos; deslizador,
  candado por fila y botón de repartir por igual. El total se queda en 100.
- `La lista de llamadas se refresca sola` mientras haya alguna procesándose, y se detiene
  cuando todas terminan.
- `N+1 del panel` resuelto (`selectinload` en `done_analyses`).
- `Rescate de llamadas atascadas` a los 20 minutos.
- `Acciones en lote`: selección múltiple, asignación masiva y borrado.
- `Código muerto retirado`: `get_rubric_weights`, `isUnassigned`, `useCallStatus`.

## Fase 0 — Que la demo exista
- `Conversaciones de demostración` (`scripts/demo_conversations.py`): seis guiones en
  español, dos por ejecutivo, con tiempos **medidos sobre el audio real**; y las seis
  grabaciones a calidad telefónica en `backend/demo_audio/`.
- `Seed de demostración` (`scripts/seed_demo.py`): 67 llamadas en 90 días con tendencias
  intencionadas (María sube, Lucía baja, Carlos estable). Semilla fija, sin IA, sin coste.
- `Cuenta pública de solo lectura`: `users.is_readonly` (**migración 0008**). El
  guardarraíl vive en `get_current_user`, así que ningún endpoint nuevo se lo salta.
- `README público` con capturas.

## Modelo de IA actualizado (Groq)

- `Fix`: el analisis fallaba en produccion con `404 model_not_found`. Groq dejo de dar
  acceso a `llama-3.3-70b-versatile` para esta cuenta, aunque su documentacion seguia
  listandolo como modelo de produccion. Pasa a **`openai/gpt-oss-120b`** en
  `render.yaml`, `config.py`, los `.env(.example)` y `AGENTS.md`.
- `Verificado de punta a punta en produccion`: se sintetizo una llamada de venta en
  espanol, se subio, Whisper la transcribio en 11 segmentos correctos y el modelo la
  puntuo (79/100) detectando que el ejecutivo esquivo la pregunta sobre intereses.
- La transcripcion (Whisper) nunca estuvo afectada: el fallo era solo del LLM.

## Reconstruccion de produccion, vigilancia y arreglo de sesion

- `Infraestructura`: la PostgreSQL del plan gratuito de Render **caducó y fue
  eliminada**; el backend llevaba dos meses muriendo al arrancar y **los datos de
  producción se perdieron** (no había copia). Sin nada que migrar, se recreó todo ya
  con el nombre nuevo: `callaibrate-api` + `callaibrate-db`, y las URLs pasaron a
  `callaibrate-api.onrender.com` y `callaibrate.vercel.app` (el dominio anterior
  quedó como redirect 307, de modo que hay un único origen). Detalle y lecciones en
  `docs/RENOMBRADO_INFRA.md`.
- `Fix`: **la recarga de página cerraba la sesión.** `AuthGuard` y la página raíz
  decidían antes de que `zustand/persist` rehidratara el store, así que el token
  siempre era `null` en el primer render y expulsaban al usuario al login en cada
  F5. Se añadió `useAuthHydrated()` en `lib/auth.ts` y ambas esperan a que la
  rehidratación termine. La raíz, además, ahora envía al asesor a `/mi-panel`.
- `Vigilancia`: el keepalive terminaba en `|| true`, así que se tragaba la caída —
  por eso el backend estuvo dos meses muerto sin que nadie se enterara. Ahora
  reintenta 3 veces y **falla con un diagnóstico** si `/health` no responde.
- `Backups`: nuevo `.github/workflows/backup-db.yml` (volcado diario con `pg_dump`,
  artefacto a 30 días). Necesita el secreto `DATABASE_URL`; si falta, avisa sin
  fallar. Los dumps contienen transcripciones, así que quedan anotados en
  `COMPLIANCE_CHECKLIST.md`.

## Rebrand a CallAIbrate + reproductor, export CSV y seguridad
- `Marca`: nueva identidad **CallAIbrate** con `docs/BRAND.md` como fuente de verdad.
  Paleta **paper `#F5F1E8`** / **ink `#2A2420`** con acentos **rust `#B8441F`** y
  **gold `#A67C27`**; tipografías **Manrope / Inter / IBM Plex Mono** vía
  `next/font/google` (esta última **solo** para datos numéricos). Se retiran la paleta,
  la tipografía y los logos de la identidad anterior (descrita en
  [`HISTORIA.md`](HISTORIA.md)); `frontend/public/fonts` y `public/brand` se
  **eliminan** (además, las woff2 eran tipografía con licencia).
- `Formas`: la clase de chaflán octogonal se sustituye por radios de **8 px**
  en contenedores (`rounded-card`) y **6 px** en controles (`rounded-control`). Los
  círculos (avatares, puntos de estado, barras de progreso) se conservan.
- `Wordmark`: `frontend/components/brand/logo.tsx` exporta `<Waveform />` y
  `<Wordmark />` como SVG real; el fragmento "AI" siempre en rust. Nuevo `favicon.svg`.
- `Copy`: titulares en caso frase (se retira `text-transform: lowercase`), conservando
  el resalte `.hl` de una palabra clave, ahora en rust.
- `Modo oscuro`: se mantiene, con paleta derivada documentada en el addendum de `BRAND.md`.
- `Reproductor de audio sincronizado`: nuevo `GET /api/v1/calls/{id}/audio` (con el
  mismo control de acceso que el detalle, y 404 explicativo si el almacenamiento perdió
  el archivo) y `components/calls/transcript-player.tsx`, que resalta el segmento que
  suena y salta al hacer clic. El audio se descarga como blob porque `<audio src>` no
  puede enviar la cabecera `Authorization`.
- `Exportación CSV`: nuevo `GET /api/v1/dashboard/report.csv` (solo admin/jefe), una
  fila por ejecutivo con las 7 dimensiones, BOM UTF-8 para Excel, y botón en el
  dashboard que respeta los filtros activos.
- `Seguridad`: el seed **genera contraseñas aleatorias** (fijables con
  `SEED_ADMIN_PASSWORD` / `SEED_JEFE_PASSWORD` / `SEED_ASESOR_PASSWORD`), las imprime
  una sola vez, migra los emails `@callqa.com` a `@callaibrate.com` conservando la
  cuenta, y **rota** cualquier cuenta sembrada que aún use una de las contraseñas que
  llegaron a estar publicadas en el repo. Se retiran las credenciales literales de
  README y docs.
- `Seguridad`: guardarraíl que **aborta el arranque** si `APP_ENV=production` con el
  `JWT_SECRET` de ejemplo.
- `Corrección`: `datetime.utcnow()` (obsoleto) sustituido por un helper explícito en
  `dashboard_service.py` que devuelve UTC *naive*, para poder comparar con las columnas
  `DateTime` sin zona horaria.
- `Docs`: `BRAND.md` y `COMPLIANCE_CHECKLIST.md` nuevos; `DESIGN.md` reescrito;
  `CallQA_AI_Presentacion.pptx` eliminado (marca antigua + credenciales demo dentro).
- `Tests`: 78 → **87** (audio: 200/404/403; CSV: contenido, filtro de campaña y 403 de
  asesor; guardarraíl de `JWT_SECRET`).

---

Las entradas anteriores al rebrand están en [`HISTORIA.md`](HISTORIA.md).
