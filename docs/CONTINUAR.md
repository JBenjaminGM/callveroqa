# Continuar el trabajo

> **Lee esto primero si acabas de entrar al proyecto.** Es el traspaso entre sesiones:
> dónde estamos, qué sigue y qué te va a hacer perder tiempo si no lo sabes.
>
> Última actualización: 25 sep 2026, tras el renombrado total a CallVeroQA y la tanda
> de producción (cuentas, retención de datos, motivos de llamada).

---

## En una frase

CallVeroQA es una plataforma de control de calidad de llamadas con IA para call centers
de banca. **El objetivo cambió: ya no es solo portafolio, es dejarla lista para vender.**
Eso reordena las prioridades, y están escritas en
**[`PLAN_PRODUCCION.md`](PLAN_PRODUCCION.md)**, que es el documento que manda ahora: qué
bloquea una venta, qué está hecho y qué depende del dueño (dinero y cuentas externas).

Antes de tocar nada, lee **[`AGENTS.md`](AGENTS.md)** (cómo está construido y sus
*gotchas*) y **[`ACUERDOS.md`](ACUERDOS.md)** (qué se decidió y qué costaría cambiarlo).
La comparativa con la competencia y el orden de las mejoras de producto están en
**[`COMPETENCIA.md`](COMPETENCIA.md)**.

## Dónde trabajar

```
C:\Users\master\dev\callveroqa
```

Rama `main`, sin worktrees. **No trabajes desde OneDrive**: Docker falla ahí con los
archivos "solo en la nube", y esa copia duplicada se borró a propósito.

Arranque en local **sin Docker** (esta máquina todavía no tiene WSL2 activo):

```
powershell -ExecutionPolicy Bypass -File ops\dev-local.ps1
```

Levanta un PostgreSQL portátil (binarios en `dev\.pgtools`, datos en `dev\.pgdata`,
usuario y base `callveroqa`), la API en modo inline y el frontend desde su build. Con
`-Stop` lo para todo. Si tocas la interfaz, `npm run build` antes de relanzar: el script
sirve el build de producción, no el servidor de desarrollo.

El entorno de Python vive en `backend\.venv` (Python 3.11, la misma versión que la imagen
de Docker). **Si renombras o mueves la carpeta del proyecto hay que recrearlo**: sus
lanzadores llevan la ruta incrustada y fallan en silencio.

## Estado exacto

| | |
|---|---|
| Repositorio | `github.com/JBenjaminGM/callveroqa` (espejo limpio: `callveroqa-public`) |
| Rama | `main`, al día con `origin` |
| Tests backend | **209**, todos en verde |
| Migraciones | 0001–0016 |
| Producción | Render + Vercel, desplegado y verificado el 24 sep 2026 |
| Sin subir | rama `infra/renombrar-servicios` (ver abajo) |

**Se hace `push` a `main` sin preguntar** (el usuario lo pidió expresamente), sabiendo que
despliega solo: Vercel reconstruye el frontend y Render aplica migraciones y vuelve a
sembrar.

---

## Lo pendiente que NO es código (esto sí bloquea)

1. **Scope `workflow` de GitHub.** El token no puede modificar `.github/workflows`, así
   que los dos workflows conservan el nombre anterior en comentarios y en la URL del
   ping. Se concede con `gh auth refresh -h github.com -s workflow` aprobando el código
   en <https://github.com/login/device>.
2. **Renombrar los servicios en Render y el proyecto en Vercel.** Está preparado en la
   rama **`infra/renombrar-servicios`** y **no se subió a propósito**: cambiar los
   nombres en `render.yaml` no renombra nada — Render trata los servicios por nombre,
   crearía unos nuevos y dejaría huérfanas la base de datos y la `GROQ_API_KEY`, que solo
   vive en el panel. Orden correcto: renombrar en los paneles de Render y Vercel →
   actualizar allí `CORS_ORIGINS` y `NEXT_PUBLIC_API_URL` → conceder el scope → subir esa
   rama. Hasta entonces las URLs vivas siguen siendo `callaibrate-api.onrender.com` y
   `callaibrate.vercel.app`, aunque la documentación ya nombra las nuevas.
3. **Decisiones de gasto** (`PLAN_PRODUCCION.md` §4): plan de pago de Render —la base
   gratuita caduca a los 30 días y ya se perdieron los datos una vez—, cuenta de S3 para
   que los audios sobrevivan a un despliegue, `GROQ_API_KEY` válida en Render, dominio
   propio y el secreto `DATABASE_URL` en GitHub para que corran las copias de seguridad.

---

## Lo que ya está hecho

### Septiembre 2026 · Renombrado total y tanda de producción

**Marca.** El rebrand a CallVeroQA se completó hasta el final: repositorios, carpeta
local, usuario y base de datos, y las claves de `localStorage` (`callveroqa-auth`,
`callveroqa-theme`). Lo único que conserva los nombres viejos son los mapas de migración
de cuentas del seed (`@callaibrate.com` y `@callqa.com` → `@callveroqa.com`): sin ellos
se duplicarían los usuarios ya creados. Ver `ACUERDOS.md` A-01.

**Cuentas** — era el bloqueante número uno, porque no se podía crear una cuenta ni
cambiar una contraseña sin entrar a la base de datos. Pantallas `/usuarios` y
`/mi-cuenta`; `GET`/`POST /users`, `PATCH /users/{id}`, `POST /users/{id}/reset-password`
y `POST /auth/change-password`. Migración 0012 (`users.active`): dar de baja cierra el
acceso en la siguiente petición y conserva el historial. Nunca se puede dejar la
plataforma sin un administrador activo.

**Datos.** Retención de grabaciones configurable (migración 0013): pasados N días se
borra el audio y **se conservan transcripción y nota**; 0 = no caduca. Y supresión total
de los datos de una persona (`DELETE /agents/{id}/data`, solo administradores).

**Operación.** `/health` comprueba también la base de datos (503 si no responde);
`X-Request-ID` en cada respuesta, en los logs de esa petición y en los errores 500; y el
proveedor S3 falla al arrancar si está mal configurado en vez de perder el primer audio.

**Producto** (de `COMPETENCIA.md`): evidencia por nota con saltos al audio, criterios
críticos con auto-fail, búsqueda dentro de las transcripciones y **motivos de llamada**
(migración 0014, `GET /dashboard/topics` y la tarjeta «Por qué llaman»).

**Coaching medible** (migración 0015, `COMPETENCIA.md` 3.3): sesión con un asesor sobre
un criterio de la rúbrica, medida con el antes y el después de 30 días **descontando lo
que se movió el equipo**. Tarjeta «Coaching» en la ficha del ejecutivo y en «Mi
rendimiento». Probándolo contra los datos reales salió que, a los cinco días de una
sesión, el asesor ya tenía tres llamadas y el equipo no, y se le daba por buena con el
cambio bruto: ahora, si hay equipo pero faltan sus datos, el veredicto espera.

**Criterios «no aplica»** (migración 0016, `COMPETENCIA.md` 3.4): una categoría marcada
como «puede no aplicar» sale de la nota cuando no se dio la situación que evalúa, y su
peso se reparte. Vienen activadas en objeciones y promociones. **Falta verlo con la IA
real**: en local no hay `GROQ_API_KEY`, así que se probó el pipeline completo contra
PostgreSQL con la respuesta de la IA simulada. Lo primero con una clave válida es subir
una llamada de consulta (sin venta ni objeciones) y comprobar que la IA devuelve `null`
en esas dos y nota en el resto.

**Dos fallos que solo aparecieron probando contra el sistema real:** el login limitaba
cinco intentos **por IP** —y un call center entero sale por una sola IP pública, así que
el sexto empleado del día no entraba—, y la purga de retención borraba audios que otras
llamadas vigentes compartían.

### Fase 0 · Que la demo exista (`26a6c55`)
- `backend/scripts/demo_conversations.py`: seis conversaciones en español, dos por
  ejecutivo (una que cumple el protocolo y otra que falla), con tiempos **medidos sobre
  el audio real**, no estimados.
- `backend/demo_audio/`: las seis grabaciones a calidad telefónica (8 kHz mono).
- `backend/scripts/seed_demo.py`: 67 llamadas en 90 días con tendencias intencionadas
  (María sube 64→85, Lucía baja 87→78, Carlos estable). Semilla fija, sin IA, sin coste.
- Cuenta de demostración de solo lectura (`users.is_readonly`, migración 0008). El
  guardarraíl vive en `get_current_user`, así que ningún endpoint nuevo se lo salta.
- README público con capturas (`capturas/`).

### Fase 1 · Quitar fricciones (`8164736`)
- **Pesos de la rúbrica relativos**: mueves uno y los demás se reajustan solos. Deslizador,
  candado por fila y botón de repartir por igual.
- La lista de llamadas **se refresca sola** mientras haya alguna procesándose.
- **N+1 del panel** resuelto (`selectinload` en `done_analyses`).
- **Rescate de llamadas atascadas** a los 20 minutos.
- **Acciones en lote**: selección múltiple, asignación masiva y borrado.
- Código muerto retirado (`get_rubric_weights`, `isUnassigned`, `useCallStatus`).

### Fase 2 · Calibrar — el diferencial del proyecto
Hasta aquí la IA puntuaba y su palabra era definitiva. Ahora hay una segunda opinión y,
sobre todo, una forma de medir en qué se diferencian.

- **Revisión humana** (`reviews`, migración 0009). El jefe corrige las puntuaciones por
  dimensión y escribe el motivo. **La nota de la IA no se pisa nunca**: son dos registros
  distintos sobre la misma llamada, y el detalle muestra las dos con su diferencia.
  El global lo pondera el backend con la rúbrica, la misma fórmula que usa la IA — si
  cada lado usara la suya, compararlas no significaría nada.
- **Sesión a ciegas** (`/calibracion`). `GET /calibration/calls/{id}` devuelve audio y
  transcripción **sin el análisis**: el score de la IA no llega al navegador, así que la
  ceguera no depende de que la interfaz lo oculte. Hay un test que lo comprueba.
- **Panel de acuerdo.** Por dimensión: sesgo (humano − IA), desviación media absoluta y
  % de acuerdo dentro de ±5 puntos. Ordena por desviación media, no por sesgo: el sesgo
  se cancela entre llamadas y la desviación no, así que una dimensión puede tener sesgo
  cero y estar pésimamente calibrada. La peor se destaca arriba con el enlace para
  reescribir la rúbrica.
- **La demo no abre vacía**: `seed_demo.py` siembra 22 revisiones con una discrepancia
  deliberada en «Manejo de objeciones» (~19 puntos frente a ~3 del resto) y otra en
  «Asertividad» con sesgo casi nulo pero desviación alta — las dos historias que el panel
  sabe distinguir. Se rellenan también en bases que ya tenían llamadas.
- Lo hace el rol `jefe` que ya existía, sin roles nuevos. El asesor no entra a
  `/calibracion` (guardado en `auth-guard.tsx` y con `require_manager` en la API), pero sí
  ve la revisión de sus propias llamadas.

### Fase 3 · Cerrar el ciclo
La evaluación era un monólogo y el panel abría con medias, que no dicen qué hacer.

- **El asesor responde** (`acknowledgements`, migración 0010). Da la evaluación por leída,
  se explica y —si la nota no le parece justa— pide revisión; el jefe contesta en el mismo
  sitio. Lo firma **quien fue evaluado**: un jefe no puede acusar recibo en su nombre, y
  hay un test que lo fija. Reabrir una petición borra la respuesta anterior, para que no
  pase por contestada sin que nadie haya leído lo nuevo.
- **El panel abre con «a quién escuchar hoy»**: como mucho cinco llamadas, cada una con
  su motivo. Cuatro motivos en orden de urgencia — petición de revisión abierta, banda
  roja sin escuchar, muy por debajo de la media del propio asesor, y asesor del que nadie
  ha escuchado nada. **Manda el motivo, no la nota**: una roja siempre puntuará menos que
  una llamada recurrida, y ordenar por nota colaría la roja por delante de una persona
  esperando respuesta. Cada llamada sale **una sola vez**, con su motivo más fuerte.
- **El panel del asesor abre con lo que tiene sin leer**, antes que su promedio.
- **Subir una carpeta entera arrastrándola**, a cualquier profundidad. `readEntries`
  devuelve los hijos por tandas: hay que insistir hasta que conteste vacío o una carpeta
  con muchas grabaciones llega cortada. Hay también un botón «elegir una carpeta» para
  navegadores sin arrastre de directorios.
- El seed siembra seis respuestas de asesores, dos con petición abierta. Van a llamadas
  **recientes y flojas** a propósito: fuera de los últimos 30 días no se verían en el
  panel, y nadie recurre un sobresaliente.

### Fase 4 · Documentación coherente
- **`HISTORIA.md`** absorbe la línea del tiempo (que se ha eliminado) y **las entradas del
  changelog anteriores al rebrand**, movidas tal cual, sin reescribir una coma:
  reescribirlas dejaría falsas frases que en su momento fueron ciertas.
- El `CHANGELOG.md` vigente arranca en CallVeroQA y recoge ya las fases 0 a 3.
- `ACUERDOS.md` se queda solo con acuerdos vigentes: fuera el que era historia con
  formato de acuerdo, y dentro tres nuevos de las fases 2 y 3 (la nota de la IA no se
  sobrescribe, el acuse lo firma quien fue evaluado, la sesión ciega lo es en el
  servidor). Van del A-01 al A-20, sin huecos.
- Cifras al día en `ARQUITECTURA.md`, `AGENTS.md` y `CLAUDE.md`: 127 tests, 10 tablas,
  10 migraciones, 54 operaciones de API, 20.213 líneas.
- **Objetivo comprobable, cumplido**: buscar el nombre o las identidades visuales
  anteriores en todo el repositorio solo da resultados dentro de `HISTORIA.md`.

  ```bash
  grep -rn "Minsait\|ForFuture\|Pruno\|chamfer\|Aetheric\|CallQA AI" --include="*.md" --include="*.ts" --include="*.tsx" --include="*.py" --include="*.css" . | grep -v node_modules | grep -v HISTORIA.md
  ```

### Pasada de diseño (11 sep)
Dos revisiones con skills de terceros sobre la interfaz ya terminada, sin tocar lógica.
El detalle está en el `CHANGELOG.md`. Lo que conviene saber para no deshacerlo:

- **Las duraciones y curvas salen de `globals.css`**, no se escriben a mano. Si añades
  movimiento, usa `--ease-out` / `--duration-*` o las utilidades `duration-ui`,
  `ease-out-strong`.
- **La `Card` no lleva sombra ni animación de entrada, a propósito.** La elevación se
  declara una sola vez (el borde) y la entrada va en el contenedor de la pantalla.
- **Los contenedores dentro de una tarjeta no llevan borde**: el fondo `bg-bg-secondary`
  ya los separa.
- **`hoverOnlyWhenSupported` está activo** en Tailwind: todos los `hover:` compilan
  dentro de `(hover: hover) and (pointer: fine)`. No hace falta envolverlos a mano.

---

## Lo que sigue

El orden está en **[`PLAN_PRODUCCION.md`](PLAN_PRODUCCION.md)**. Lo que queda por
programar, de más a menos valor:

1. **Alertas de críticos por asesor y tendencia** (ya existe la alerta por llamada y el
   porcentaje por campaña; falta la serie temporal).
2. **Multi-cliente** (3.5): solo si se vende a más de una empresa. Es una reforma grande
   —hay que llevar el identificador de cliente a todas las tablas y consultas— y **no
   hace falta** para vender una instalación a un banco.

Dos avisos si retomas esto dentro de un tiempo:

- **La base de datos de producción vuelve a caducar a los 30 días.** Si la demo abre
  vacía, es eso (punto 9 de los tropiezos).
- **Antes de tocar la marca o la documentación**, lee [`HISTORIA.md`](HISTORIA.md): es el
  único sitio donde se nombran el producto y las identidades visuales anteriores, y
  conviene que siga siendo así.

---

## Cómo verificar que todo sigue bien

Tests del backend (209):

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
```

Frontend:

```bash
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

Levantar la aplicación en local (sin Docker, que es como está montada esta máquina):

```bash
powershell -ExecutionPolicy Bypass -File ops/dev-local.ps1
```

App en <http://localhost:3000>, API en <http://localhost:8000/docs>. Con Docker (si algún
día hay WSL2) sigue valiendo `docker compose up -d --build`.

**Cuenta de demostración:** `demo@callveroqa.com` / `CallVeroQA-Demo-2026` (solo lectura).
Las contraseñas de admin y jefe se generan al azar en cada base nueva y se imprimen una
sola vez; en esta máquina quedaron en `dev\.seed-output.txt`. Desde la aplicación,
cualquiera puede cambiarse la suya en **Mi cuenta**, y un administrador puede resetear la
de otro desde **Usuarios**.

Comprobación rápida de que la demo sigue contando la historia correcta: el panel abre con
«a quién escuchar hoy», la tarjeta «Por qué llaman» muestra tres motivos, y
«Oferta de tarjeta Premium» es el peor (score ~50, con 10 llamadas suspendidas).

---

## Lo que te hará perder tiempo si no lo sabes

1. **Si mueves o renombras la carpeta del proyecto, `backend\.venv` deja de funcionar**:
   sus lanzadores (`alembic.exe`, `pytest.exe`) llevan la ruta incrustada y fallan **sin
   mensaje**. Hay que recrear el entorno.
2. **No trabajes desde OneDrive.** Docker falla con los archivos "solo en la nube" y
   además el borrado de una carpeta ahí puede quedar bloqueado por el sincronizador.
3. **`npm start` sobrevive a que se mate la tarea.** Si el navegador muestra una versión
   antigua o la página sale en blanco con 404 de todos los *chunks*, es un servidor viejo
   sirviendo un build que ya no existe. `ops/dev-local.ps1` ya lo mata antes de arrancar.
4. **Las columnas de fecha son *naive*.** Nunca compares con un `datetime` con zona
   horaria: usa `datetime.now(timezone.utc).replace(tzinfo=None)`.
5. **Las columnas JSON guardan `None` como `null` JSON, no como NULL de SQL.** Para
   filtrar «tiene fallos críticos» se usa `uncapped_score IS NOT NULL`, que sí es un NULL
   de verdad.
6. **`useAuthStore.persist` no existe durante el prerender.** Solo se puede leer dentro de
   un `useEffect`; hacerlo en el cuerpo del componente rompe `next build`.
7. **El seed de demostración reutiliza seis audios entre 67 llamadas.** Cualquier cosa que
   borre archivos (retención, limpiezas) tiene que comprobar si otra llamada vigente
   comparte el archivo, o deja mudas llamadas que no han caducado.
8. **El catálogo de modelos de Groq cambia sin avisar.** Si el análisis da `404
   model_not_found`, elige otro de <https://console.groq.com/docs/models> y cámbialo en
   `render.yaml` **y** en la variable `AI_MODEL_GROQ` del panel de Render.
9. **La PostgreSQL del plan gratuito de Render caduca a los 30 días** y se elimina con
   todo dentro. Ya pasó una vez. El workflow de copias existe pero necesita el secreto
   `DATABASE_URL` en GitHub.
10. **Al redesplegar se borran los audios** con `STORAGE_PROVIDER=local`. Es el motivo por
    el que S3 es el modo de producción, no un extra.

## Cómo trabajar en este proyecto

- **De forma autónoma**: git, dependencias, migraciones, pruebas, builds y `push` a `main`
  sin pedir confirmación paso a paso. El usuario lo pidió así expresamente.
- **Nada se da por bueno sin probarlo de verdad** contra el sistema real. Así aparecieron
  los fallos que nadie habría visto leyendo el código: la base de datos borrada, la sesión
  que se cerraba al recargar, el modelo de Groq retirado, el límite de login por IP y la
  purga que borraba audios compartidos.
- **No introduzcas claves ni contraseñas reales en formularios.** Configurar, diagnosticar,
  desplegar y verificar, sí; escribir una API key o una contraseña del usuario en un
  campo, no: eso lo hace él.
- **Pregunta antes de** borrar datos o renombrar servicios en la nube.
- **Escribe en español**, igual que el resto del proyecto, y con comentarios que expliquen
  *por qué*, no *qué*.
