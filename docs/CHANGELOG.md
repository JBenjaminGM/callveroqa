# Changelog — CallVeroQA

Cambios relevantes. Formato: descripción (commit). Lo más nuevo arriba.

> Arranca en el rebrand a CallAIbrate (hoy CallVeroQA). Lo anterior está en
> [`HISTORIA.md`](HISTORIA.md), movido tal cual: nombra el producto y la identidad
> visual de entonces porque así era. Es historia, no estado.

## Producto y operación: suspendidas por asesor, Sentry y tres fallos de producción

**Suspendidas por criterio crítico, por asesor y en el tiempo.** La alerta por llamada
ya existía; faltaba el patrón. Es el punto 3 del plan de [`COMPETENCIA.md`](COMPETENCIA.md).

- `GET /dashboard/critical` [manager]: tasa del periodo, serie semanal, tasa por asesor
  (con la de cada mitad del periodo y su criterio más incumplido) y criterios más
  incumplidos.
- `Alertas nuevas`: `critical_agent` (dos o más suspensiones de una persona en el
  periodo) y `critical_trend` (la tasa sube 15 puntos o más entre la primera y la segunda
  mitad, del equipo o de una persona). Con menos de 3 llamadas en una mitad no se mide.
- `Orden de las alertas`: dentro de una severidad, primero los patrones (una persona o el
  equipo) y después las llamadas sueltas. Ordenar solo por `value` los enterraba: mezcla
  una nota con un porcentaje, y la subida de Lucía salía en el puesto 18.
- `Interfaz`: tarjeta «Llamadas suspendidas» en el panel (barras por semana con el eje
  ajustado a los datos, tabla por asesor con tendencia) y enlace a `/calls?critical=true`,
  que ahora sí aplica el filtro al abrir. `DeltaPill` admite `higherIsBetter`: una subida
  de suspendidas es roja y con la flecha hacia arriba.

**Monitorización (Sentry).** Integrado y apagado mientras no haya `SENTRY_DSN`. Sin
cuerpos de petición, sin datos personales y **sin variables locales**: por defecto Sentry
las envía, y el test comprobó que ahí iba el token de la petición entero. Cada evento
lleva el `request_id`.

**Tres fallos que solo se veían contra producción:**

- **El 500 salía con `request_id: null`** y sin cabecera `X-Request-ID`: el manejador
  global corre fuera del middleware, cuando el id ya se ha limpiado. Ahora se responde
  dentro del middleware.
- **La demo pública no tenía audio.** El disco de Render se vacía en cada despliegue y
  el seed solo copiaba los audios al crear las llamadas: sin reproductor ni saltos al
  audio desde la evidencia. Ahora el seed los repone en cada arranque (y, con S3, los
  sube allí solo).
- **La copia de seguridad diaria nunca había funcionado**: `pg_dump` 16 contra
  PostgreSQL 18. El arreglo (con la copia cifrada, porque el repositorio es público) está
  en la rama `infra/backup-cifrado`, a falta del scope `workflow`.

**Demo:** el seed corrige la fecha de sus propias sesiones de coaching si no enseñan el
desenlace previsto (en producción, la de Lucía salía «funcionó»). Solo toca las que él
mismo sembró.

**Documentación:** [`PASOS_DEL_DUENO.md`](PASOS_DEL_DUENO.md), con todo lo que queda en
manos del dueño, paso a paso.

- `Tests`: 209 → **216**.

## Producto: criterios «no aplica»

Una llamada de consulta de saldo puntuaba cero en «manejo de objeciones» porque no hubo
objeciones, y cero en «promociones» porque no era de venta. La nota bajaba por algo que
el asesor no tuvo ocasión de hacer. Es el punto 3.4 de [`COMPETENCIA.md`](COMPETENCIA.md)
(lo que MaestroQA y Scorebuddy llaman preguntas «N/A»).

- `Rúbrica` (**migración 0016**): cada categoría puede marcarse como «puede no aplicar»,
  con una condición escrita por el jefe («solo si el cliente plantea una objeción»). La
  migración la activa una sola vez en objeciones y promociones; si el jefe la quita,
  ningún arranque se la vuelve a poner.
- `IA`: el prompt solo ofrece `null` en esas categorías y le pide que explique por qué no
  aplica. Lo que la IA deja en blanco en una categoría que **no** lo permite no se le
  regala: cuenta como cero, igual que si la hubiera omitido.
- `Nota global`: las categorías que no aplican salen del denominador y su peso se reparte
  entre las demás. Sin ninguna «no aplica», la fórmula da exactamente lo mismo que antes.
  Se guardan en `analyses.not_applicable`.
- `Críticos`: un incumplimiento crítico en una categoría que la IA dio por no aplicable
  es una contradicción, y no suspende la llamada.
- `Revisión humana`: el jefe también puede marcar «no aplica» (en la revisión y en la
  sesión a ciegas); se guarda omitiendo esa categoría, que la revisión ya ponderaba así.
- `Interfaz`: el detalle de la llamada y el PDF enseñan las categorías que no aplicaron,
  con su porqué, en vez de hacerlas desaparecer.
- `Arreglo`: un análisis sin recomendaciones (la columna admite nulo) tumbaba el detalle
  de la llamada con un 500.
- `Tests`: 199 → **209**.

## Producto: coaching medible

Hasta aquí el coaching era un acto de fe: el jefe hablaba con el asesor y nadie volvía
a mirar si sirvió. Es el punto 3.3 de [`COMPETENCIA.md`](COMPETENCIA.md) y lo que piden
todas las guías de compra: **coaching conectado con los hallazgos y con resultado
medible**.

- `Sesión de coaching` (**migración 0015**, `coaching_sessions`): con un asesor, sobre
  **un** criterio de la rúbrica, en una fecha, con notas y la llamada que la motivó.
  Ir atada a un criterio es lo que permite medirla.
- `Antes y después`: la nota de ese criterio en los 30 días anteriores frente a los 30
  posteriores. **Se descuenta lo que se movió el resto del equipo** en esas mismas
  semanas: si todos suben (cambió la rúbrica, la campaña o el modelo), eso no es mérito
  de la sesión. Con menos de 3 llamadas a un lado no hay veredicto («faltan llamadas» o
  «sin línea base»), y el propio día de la sesión no cuenta en ningún lado.
- `La medida no se guarda`: se calcula al leer, así sigue siendo cierta cuando entran
  llamadas nuevas o se reasigna una.
- `Sugerencia de criterio`: al registrar una sesión se proponen los criterios donde el
  asesor más se separa **del equipo**, no los de nota más baja — si todos puntúan bajo en
  algo, el problema es de la rúbrica o del producto y un coaching individual no lo arregla.
- `API`: `GET`/`POST /coaching/sessions`, `GET`/`PATCH`/`DELETE /coaching/sessions/{id}`
  y `GET /coaching/suggestions/{agent_id}`. Registrar, corregir y borrar es de manager;
  el asesor ve las suyas (y solo las suyas) en su panel.
- `Interfaz`: tarjeta **Coaching** en la ficha del ejecutivo (con alta) y en «Mi
  rendimiento» (lectura). Cada sesión enseña su veredicto, las cuatro cifras (antes,
  después, equipo, efecto neto), las llamadas de la ventana como puntos y una frase que
  explica el veredicto con sus números: sin ella, «no funcionó» junto a una nota que
  subió parece un error.
- `Supresión de datos`: `DELETE /agents/{id}/data` borra también las sesiones de
  coaching. Cuelgan de la ficha, que se conserva, así que no caían en cascada.
- `Demo`: tres sesiones que cuentan tres historias — la de María funciona, la de Lucía
  no se separa de lo que hizo el equipo y la de Carlos es demasiado reciente para
  juzgarla. Se fechan desde la última llamada sembrada, no desde hoy.
- `Arreglo`: `formatDate` enseñaba las fechas sin hora (`call_date`) un día antes en
  América, porque `Date` las lee como medianoche UTC.
- `Tests`: 187 → **199**.

## Producto: por qué llaman los clientes (motivos de llamada)

El resto del panel mide al equipo; esto mide **a qué se enfrenta**. Es el punto 3.2 de
[`COMPETENCIA.md`](COMPETENCIA.md) y el salto de «control de calidad» a «inteligencia de
cliente»: un jefe puede entrenar a un asesor flojo, pero si el 30 % de las llamadas
entran por un cobro mal explicado, eso no se arregla con coaching.

- `Motivo detectado por la IA` en cada llamada (**migración 0014**, `calls.topic`).
- `GET /dashboard/topics` [manager] y tarjeta **«Por qué llaman»** en el panel: volumen,
  nota media, % en banda roja y suspendidas por motivo, ordenado por volumen — lo primero
  que hay que ver es de qué tamaño es el problema, no cuál puntúa peor.
- `El vocabulario no se fragmenta`: a la IA se le pasa el catálogo de motivos ya usados
  para que reutilice uno si encaja, y al guardar se normaliza (espacios, mayúsculas,
  acentos) y se busca un equivalente. También se limpia la basura típica del LLM
  («Motivo: …», comillas, una frase entera en vez de una etiqueta).
- `Demo`: los seis guiones traen su motivo y las bases ya sembradas se rellenan sin
  duplicar. En la demo, «Oferta de tarjeta Premium» es el peor motivo (≈50) y concentra
  10 de las llamadas suspendidas.
- `Tests`: 180 → **187**.

## Producción: cuentas, retención de datos y operación

Sale de [`PLAN_PRODUCCION.md`](PLAN_PRODUCCION.md), que ordena lo que falta para
que un cliente pueda pagar por esto. Aquí están los bloqueantes cerrados.

**Cuentas** (antes no existían: las contraseñas las generaba el seed y se
imprimían una vez):

- `GET`/`POST /users`, `PATCH /users/{id}`, `POST /users/{id}/reset-password`
  (gestión) y `POST /auth/change-password` (cualquiera, sobre su cuenta, pidiendo
  la actual). Pantallas `/usuarios` y `/mi-cuenta`.
- **Migración 0012** (`users.active`). Dar de baja no borra: cierra el acceso en
  la siguiente petición —no cuando caduque el token— y conserva el historial.
- Nunca se puede dejar la plataforma sin un administrador activo, ni
  desactivarse uno mismo. La cuenta demo no se administra desde la API.
- Contraseñas: mínimo 10 caracteres, no reutilizar las que llegaron a
  publicarse, no igual al email; las generadas se muestran una sola vez.
- `El límite del login pasa a contarse por IP + cuenta` (10/15 min). Contando
  solo por IP, cinco fallos de una persona dejaban fuera 15 minutos a todo un
  call center, que sale por una única IP pública.

**Datos** (lo que un banco pregunta antes de firmar):

- `Retención de grabaciones` configurable (**migración 0013**): pasados N días se
  borra el audio y **se conservan transcripción y nota**. 0 = no caduca. Corre
  sola con el uso (máx. cada 6 h) y se puede aplicar a mano desde Ajustes.
  Reproducir un audio caducado devuelve **410** explicando por qué. No borra un
  archivo que otra llamada vigente comparte.
- `Supresión de una persona`: `DELETE /agents/{id}/data`, solo administradores
  (`require_admin` nuevo), con recuento de lo borrado.

**Operación:**

- `/health` comprueba también la base de datos (503 si no responde). Un proceso
  vivo que no puede consultar nada está caído para el usuario: esa diferencia es
  la que dejó pasar dos meses de caída sin alarma.
- `X-Request-ID` en cada respuesta (se respeta el del proxy), en todas las líneas
  de log de esa petición y en el cuerpo de los errores 500.
- `S3 endurecido`: si `STORAGE_PROVIDER=s3` y falta configuración, falla al
  arrancar con un mensaje claro en vez de perder el primer audio; una ruta de
  otro bucket se rechaza en vez de inventar una clave. Con tests, sin tocar AWS.

**Alertas:** las llamadas suspendidas por criterio crítico tienen alerta propia
(se mezclaban con «banda roja», que da una lectura falsa) y la tabla por campaña
muestra su porcentaje.

- `Tests`: 147 → **180**.

## Marca: renombrado total, sin rastro del nombre anterior

El rebrand anterior dejó fuera lo que costaba dinero o sesiones. Se revisó la
decisión y se pagó el coste de una vez: repositorio `callveroqa` (+ espejo
`callveroqa-public`), usuario y base local `callveroqa`, y las claves de
`localStorage` (`callveroqa-auth`, `callveroqa-theme`). Efectos asumidos: quien
tuviera un token guardado vuelve al login una vez y el tema se resetea.

Lo único que conserva los nombres viejos son los mapas de migración de cuentas
del seed (`@callaibrate.com` y `@callqa.com` → `@callveroqa.com`), sin los cuales
se duplicarían los usuarios ya creados.

**Pendiente, y separado a propósito** (rama `infra/renombrar-servicios`): los
servicios de Render y el proyecto de Vercel. Cambiar los nombres en `render.yaml`
no los renombra — Render los trata por nombre y crearía servicios nuevos,
dejando huérfanos la base de datos y la `GROQ_API_KEY` del panel.

## Mejoras frente a la competencia: evidencia, críticos y búsqueda

Nacen de una comparación con Observe.AI, CallMiner, Zendesk QA, Level AI y otras
([`COMPETENCIA.md`](COMPETENCIA.md)). Las tres son lo mínimo que un comprador de QA con
IA pide en 2026, y aquí faltaban.

- `Evidencia por nota`: la IA devuelve por dimensión una frase de por qué y de 1 a 3
  segmentos que la respaldan (`analyses.dimension_evidence`, **migración 0011**). En la
  ficha, cada nota enseña su porqué y chips de tiempo que **saltan el audio** a ese
  momento (`TranscriptPlayer.jumpToSegment`). Saneado en `evidence_service.py`: fuera
  claves inexistentes y segmentos fuera de rango.
- `Criterios críticos (auto-fail)`: un subcriterio se marca como crítico en
  Configuración. Si se incumple, nota global 0, con `uncapped_score` (la que habría
  tenido) y `critical_failures` (qué, por qué, en qué segundo). **Solo cuenta lo que la
  rúbrica marca como crítico**: si la IA inventa uno, se descarta. Por defecto:
  «Disclaimers obligatorios» y «Sin afirmaciones prohibidas».
- `El auto-fail no contamina la calibración`: la revisión humana y el panel de acuerdo
  comparan contra la nota **sin penalizar** (`rubric_score`). Lo destapó la verificación
  en la app: una suspendida daba «IA 0 · Humano 72 · diferencia +72», que mide la regla
  y no el desacuerdo. Mismo criterio para la media del asesor en «a quién escuchar».
- `A quién escuchar hoy`: motivo nuevo `critical_failed`, justo detrás de las peticiones
  de revisión del asesor.
- `Búsqueda en lo que se dijo`: `GET /calls?q=` busca en la transcripción (comodines de
  LIKE tratados como texto) y devuelve el fragmento; el listado lo resalta. `?critical=true`
  deja solo las suspendidas, marcadas en la tabla.
- `Demo`: los seis guiones traen evidencia escrita a mano y dos de las tres llamadas
  flojas incumplen un crítico (la de préstamos es floja pero no suspende: la demo enseña
  la diferencia). Las bases ya sembradas se completan sin duplicar.
- `Tests`: 127 → **147**.

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
