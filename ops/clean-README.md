# CallVeroQA

**Calidad verificada en cada llamada.**

Un jefe de campaña sube las grabaciones de su equipo. CallVeroQA las transcribe, las
evalúa contra una rúbrica configurable y devuelve una nota del 0 al 100 con
recomendaciones concretas. Lo que antes exigía escuchar llamada por llamada —y en la
práctica se hacía sobre el 1 o 2% de ellas— se hace sobre el 100%.

🌐 **Demo en vivo:** <https://callveroqa.vercel.app>
Entra con **`demo@callveroqa.com`** / **`CallVeroQA-Demo-2026`** — cuenta de solo
lectura, con 90 días de datos de ejemplo ya cargados.

> El backend está en un plan gratuito y se duerme con la inactividad: la primera visita
> puede tardar unos 50 segundos en responder.

---

![Panel del jefe de campaña](capturas/01-dashboard.png)

## Qué hace

**Escucha y puntúa.** Transcribe con Whisper, separa quién habla, enmascara datos
sensibles y evalúa la llamada con un modelo de lenguaje contra siete criterios: saludo y
protocolo, asertividad, oferta de producto, cumplimiento normativo, resolución, manejo de
objeciones y sentimiento del cliente.

**Explica la nota.** Cada llamada trae un resumen, la puntuación de cada criterio y
recomendaciones accionables con su prioridad — no un número suelto.

**Y calibra: comprueba que la IA puntúa bien.** Es lo que hace creíble la nota y lo que
casi ningún sistema de este tipo hace. El jefe puntúa una llamada **sin ver la nota de la
IA** —la ceguera está en el servidor: el score ni siquiera se envía al navegador— y al
guardar se revelan las dos. **La nota de la IA nunca se sobrescribe**: conviven, y de su
diferencia sale un panel de acuerdo que dice en qué criterios discrepan más. Cuando uno
se desvía mucho más que el resto, el problema casi nunca es la IA: es que ese criterio de
la rúbrica admite dos lecturas. El sistema lo señala y enlaza a donde reescribirlo.

![Transcripción sincronizada con el audio](capturas/03-llamada.png)

**Reproduce y sincroniza.** El audio se escucha mientras la transcripción resalta la
frase que suena. Al hacer clic en cualquier segmento, la grabación salta a ese momento.

**Vigila el cumplimiento.** Cada campaña define su nota de producto: qué se ofrece, con
qué condiciones, qué frases son obligatorias y qué afirmaciones están prohibidas. Las
llamadas que se salen del guion aparecen como alerta.

**Mide cómo se habla.** Ratio de hablar/escuchar, porcentaje de silencio, monólogo más
largo, palabras por minuto y turnos por minuto — calculado de los tiempos reales de la
transcripción, sin IA de por medio.

![Listado de llamadas](capturas/02-llamadas.png)

**Separa lo que ve cada quien.** El jefe ve todo el equipo; el asesor solo su propio
rendimiento, con su percentil anónimo dentro de la campaña.

**Cierra el ciclo.** La evaluación no es un monólogo: el asesor acusa recibo, cuenta su
versión y puede pedir revisión de una nota; el jefe le responde. Y el panel del jefe no
abre con medias, sino con **a quién escuchar hoy y por qué** — como mucho cinco llamadas,
ordenadas por urgencia y no por nota, porque una llamada roja siempre puntuará menos que
una recurrida, y detrás de la recurrida hay alguien esperando respuesta.

## Cómo está construido

| | |
|---|---|
| **Backend** | Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL |
| **Frontend** | Next.js 14 (App Router) · TypeScript · Tailwind CSS · TanStack Query · Recharts |
| **IA** | Groq (Whisper large v3 + modelo de lenguaje). Intercambiable por OpenAI, Claude o Azure con una variable |
| **Procesamiento** | Celery + Redis, o en línea sin worker para despliegues pequeños |
| **Infraestructura** | Docker Compose en local · Vercel (frontend) + Render (backend y base de datos) |
| **Pruebas** | 127 tests de backend |

## Correrlo en local

Requisito: Docker.

```bash
docker compose up -d --build
```

- App: <http://localhost:3000>
- API y documentación interactiva: <http://localhost:8000/docs>

El arranque aplica las migraciones, crea las cuentas de ejemplo y **siembra 90 días de
llamadas de demostración** con sus grabaciones y transcripciones, para que el panel no
salga vacío. Las contraseñas de las cuentas se generan al azar y se imprimen una sola vez:

```bash
docker compose logs api | grep -A 8 CREDENCIALES
```

Para que el análisis con IA funcione hace falta una clave de proveedor en `backend/.env`
(los datos de demostración no la necesitan):

```
AI_PROVIDER=groq
GROQ_API_KEY=...
```

## Estructura

```
backend/     API FastAPI: modelos, servicios, pipeline de procesamiento, migraciones y tests
frontend/    Aplicación Next.js: páginas, componentes y visualización de datos
capturas/    Imágenes de este README
```

## Pruebas

```bash
cd backend && python -m pytest -q
```

## Despliegue

`git push` a la rama principal y Vercel y Render redespliegan solos. La configuración vive
en `render.yaml` y `docker-compose.yml`.

## Licencia

Uso privado. Todos los derechos reservados.
