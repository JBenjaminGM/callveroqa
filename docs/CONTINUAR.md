# Continuar el trabajo

> **Lee esto primero si acabas de entrar al proyecto.** Es el traspaso entre sesiones:
> dónde estamos, qué sigue y qué te va a hacer perder tiempo si no lo sabes.
>
> Última actualización: 11 sep 2026, tras la pasada de diseño.

---

## En una frase

CallVeroQA es una plataforma de control de calidad de llamadas con IA. **El destino es
un portafolio**, no vender el producto — eso decide todas las prioridades. Hemos
ejecutado un plan de cinco fases nacido de una auditoría. **Están las cinco.**

Antes de tocar nada, lee **[`ARQUITECTURA.md`](ARQUITECTURA.md)** (cómo funciona) y
**[`ACUERDOS.md`](ACUERDOS.md)** (qué se decidió y qué costaría cambiarlo).

## Dónde trabajar

```
C:\Users\master\dev\callveroqa\.claude\worktrees\laughing-kapitsa-5141df
```

Rama `claude/callveroqa-callibrate-redesign-036677`. **Es un worktree**: ejecuta todo desde
ahí, no desde la raíz del repositorio.

## Estado exacto

| | |
|---|---|
| Rama | `claude/callveroqa-callibrate-redesign-036677` |
| Último en `origin/main` | `d50afb8` — suelo de calidad (IMPECCABLE) |
| Sin subir | nada: **las cinco fases y las dos pasadas de diseño están desplegadas** |
| Tests backend | **180**, todos en verde |
| Migraciones | 0001–0013, aplicadas en producción |

**Pregunta antes de hacer `git push`.** Subir a `main` despliega solo: Vercel reconstruye
el frontend y Render aplica las migraciones y vuelve a sembrar. Verificado el 11 sep:
las 67 llamadas siguen ahí, las 22 revisiones y los 6 acuses se sembraron sobre los datos
existentes, y las nueve rutas nuevas responden.

---

## Lo que ya está hecho

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

**El plan de cinco fases está terminado.** No hay una fase 5 pendiente: lo que queda son
las decisiones abiertas de [`ACUERDOS.md`](ACUERDOS.md), que son del usuario y no
técnicas — sobre todo **D-1** (pasar Render a plan de pago, que resuelve de un golpe la
caducidad de la base, el arranque lento y, con S3, la pérdida de audios).

Si retomas el proyecto para añadir algo, dos avisos:

- **La base de datos de producción vuelve a caducar a los 30 días.** Si al abrir la demo
  no hay datos, es eso. Ver el punto 9 de los tropiezos.
- **Antes de tocar la marca o la documentación**, lee [`HISTORIA.md`](HISTORIA.md): es el
  único sitio donde se nombran el producto y las identidades visuales anteriores, y
  conviene que siga siendo así.

El plan completo, con el porqué de cada cosa, está en el artefacto
<https://claude.ai/code/artifact/0736a828-5247-4c0a-911d-71bf3c405a4f>
y la auditoría que lo originó en
<https://claude.ai/code/artifact/fb1c7a81-572f-4eef-8aa2-624149103f2a>.

---

## Cómo verificar que todo sigue bien

```bash
cd backend && "C:/Users/master/dev/callveroqa/backend/.venv/Scripts/python.exe" -m pytest -q
```

```bash
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

```bash
docker compose up -d --build
```

App en <http://localhost:3000>, API en <http://localhost:8000/docs>.

**Cuenta de demostración:** `demo@callveroqa.com` / `CallVeroQA-Demo-2026` (solo lectura).
Las contraseñas de admin y jefe se generan al azar en cada base nueva y se imprimen una
sola vez: `docker compose logs api | grep -A 8 CREDENCIALES`.

---

## Lo que te hará perder tiempo si no lo sabes

1. **`.venv` y `node_modules` viven en el repositorio principal**, no en el worktree.
   Para los tests usa el intérprete de `C:\Users\master\dev\callveroqa\backend\.venv`.
   Para el frontend hace falta `npm ci` dentro del worktree.
2. **El stack Docker del repositorio principal ocupa el puerto 8000.** Si `docker compose
   up` no arranca, párala: `docker stop callveroqa-api-1 callveroqa-worker-1
   callveroqa-postgres-1 callveroqa-redis-1`.
3. **`npx next start` sobrevive a que se mate la tarea.** Si el navegador muestra una
   versión antigua, es que quedó un servidor huérfano en el 3000: mátalo por puerto antes
   de arrancar el nuevo build.
4. **Chrome cachea agresivamente el frontend local.** Si acabas de reconstruir y ves la
   interfaz vieja, comprueba con otro navegador antes de dar por roto el código.
5. **Las columnas de fecha son *naive*.** Nunca compares con un `datetime` con zona
   horaria: usa `datetime.now(timezone.utc).replace(tzinfo=None)`.
6. **`useAuthStore.persist` no existe durante el prerender del servidor.** Solo se puede
   leer dentro de un `useEffect`; hacerlo en el cuerpo del componente rompe `next build`.
7. **Al redesplegar se borran los audios** (`STORAGE_PROVIDER=local`). Reintentar una
   llamada ya subida falla con `No such file or directory`: hay que volver a subirla.
8. **El catálogo de modelos de Groq cambia sin avisar.** Si el análisis da `404
   model_not_found`, elige otro de <https://console.groq.com/docs/models> y cámbialo en
   `render.yaml` **y** en la variable `AI_MODEL_GROQ` del panel de Render.
9. **La PostgreSQL del plan gratuito de Render caduca a los 30 días** y se elimina con
   todo dentro. Ya pasó una vez. El workflow de copias existe pero necesita el secreto
   `DATABASE_URL` en GitHub.

## Cómo trabajar en este proyecto

- **De forma autónoma**: ejecuta git, docker, dependencias, migraciones, pruebas y builds
  sin pedir confirmación paso a paso.
- **Nada se da por bueno sin probarlo de verdad** contra el sistema real. Así aparecieron
  los tres fallos que nadie habría visto: la base de datos borrada, la sesión que se
  cerraba al recargar y el modelo de Groq retirado.
- **No introduzcas claves ni contraseñas en formularios.** Configurar, diagnosticar,
  desplegar y verificar, sí. Escribir una API key en un campo, no: eso lo hace el usuario.
- **Pregunta antes de**: hacer `push`, borrar datos o renombrar servicios.
- **Escribe en español**, igual que el resto del proyecto.
