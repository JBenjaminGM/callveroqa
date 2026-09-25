# Competencia: quién resuelve lo mismo y qué nos falta

> Investigación de septiembre de 2026. Qué hacen las plataformas de QA de llamadas con
> IA, en qué destaca CallVeroQA, qué le faltaba y qué se ha hecho ya. Es la base del
> plan de mejora: cualquier prioridad nueva debería poder justificarse contra esta tabla.

---

## El mercado en una frase

Todas las plataformas serias ya **evalúan el 100 % de las llamadas** (no la muestra del
2 % de la QA manual). La competencia ya no está en puntuar, sino en **cuánto se puede
confiar en la nota y qué se hace con ella**: evidencia, calibración, coaching y
detección de riesgos.

## Quién es quién

| Plataforma | Foco | Lo que la distingue |
|---|---|---|
| **Observe.AI** | Contact center, voz | Auto QA con cada nota **trazable al momento exacto de la llamada**; coaching «basado en evidencia». |
| **CallMiner Eureka** | Analítica conversacional enterprise | **Descubrimiento de temas**, búsqueda en conversaciones, **redacción automática** de datos sensibles, alertas. |
| **NICE / Verint** | Suites enterprise (WFM + QM) | Integración con todo el stack del contact center; auto-fail y formularios condicionales. |
| **Level AI** | QA semántico | Análisis de causa raíz por intención, no por palabras clave. |
| **Zendesk QA (Klaus)** | Soporte omnicanal | **AI Trust Score**: correlación IA-humano para saber cuánto fiarse del auto QA; *Spotlight* para elegir qué revisar. |
| **MaestroQA** | Soporte / CX | Preguntas «no puntuables» de causa raíz (fallos de política o de sistema, no del agente). |
| **Scorebuddy / evaluagent** | QA para equipos medianos | Scorecards muy configurables, **auto-fail**, gamificación. |
| **Balto** | Voz en tiempo real | Guía al agente **durante** la llamada. |
| **Convin, Enthu.ai** | Mid-market, precio bajo | Auto QA + coaching automatizado a partir de llamadas marcadas. |
| **LATAM** (HaddaCloud, Link Solution, eAlicia, Walter Bridge…) | Speech analytics local | Español nativo, cumplimiento local (p. ej. Ley 21.719 en Chile), ISO 27001. |

## Qué pide un comprador en 2026

Resumen de las guías de compra consultadas (fuentes al final):

1. Cobertura del **100 %** de interacciones.
2. **Scorecard propio** con pesos, umbrales y **criterios de auto-fail**.
3. **Evidencia**: cada nota ligada al momento de la conversación que la justifica.
4. **Calibración y disputas**: poder corregir a la IA, que la corrección quede registrada y
   medir la concordancia IA-humano.
5. **Coaching** conectado con los hallazgos, no módulos genéricos.
6. **Causa raíz y temas**: qué está pasando en todo el volumen, no llamada a llamada.
7. **Búsqueda** en lo que se dijo.
8. Seguridad: redacción de datos sensibles, trazabilidad, certificaciones.

## Dónde está CallVeroQA

| Capacidad | CallVeroQA | Nota |
|---|---|---|
| 100 % de llamadas evaluadas | ✅ | Pipeline automático (Groq, portable a Claude/OpenAI/Azure). |
| Scorecard configurable | ✅ | Rúbrica dinámica: categorías, subcriterios, pesos. |
| **Auto-fail (criterios críticos)** | ✅ **nuevo** | Ver abajo. |
| **Evidencia por nota** | ✅ **nuevo** | Justificación + saltos al audio. |
| Calibración a ciegas + acuerdo IA-humano | ✅ **ventaja** | Pocos lo hacen tan explícito: la nota de la IA nunca se pisa y el cegado es en servidor. Equivale al *AI Trust Score* de Zendesk. |
| Disputa del asesor | ✅ | El asesor responde y pide revisión; el jefe contesta. |
| Priorización de escucha | ✅ **ventaja** | «A quién escuchar hoy y por qué», ahora con las suspendidas primero. |
| Nota de producto por campaña | ✅ **ventaja** | Específico de venta bancaria: la IA evalúa la oferta contra la ficha. |
| **Búsqueda en transcripciones** | ✅ **nuevo** | Con fragmento resaltado. |
| Redacción de datos sensibles | 🟡 | Enmascarado *best-effort* antes del LLM; el audio crudo sigue saliendo al proveedor. |
| **Motivos de llamada / temas** | ✅ **nuevo** | `GET /dashboard/topics` y la tarjeta «Por qué llaman»: vocabulario que crece sin fragmentarse. Falta la causa raíz agregada por intención (lo de Level AI). |
| **Coaching con seguimiento antes/después** | ✅ **nuevo** | Sesión atada a un criterio; antes/después de 30 días descontando lo que se movió el equipo. |
| Evaluación en tiempo real | ❌ | Fuera de alcance: exige integración con la telefonía. |
| Omnicanal (chat, email) | ❌ | Solo voz. |
| Integraciones CCaaS / CRM | ❌ | Subida manual de audios. |

## Lo que se ha hecho (septiembre de 2026)

### 1. Evidencia por nota
La IA devuelve por dimensión **una frase de por qué** y **de 1 a 3 segmentos** que la
respaldan. En la ficha de la llamada cada nota muestra su porqué y unos chips de tiempo
que **saltan el audio** a ese momento. El backend sanea la respuesta: descarta claves que
no existen en la rúbrica y segmentos fuera de rango (`app/services/evidence_service.py`).

### 2. Criterios críticos (auto-fail)
Cualquier subcriterio de la rúbrica se puede marcar como **crítico** en Configuración.
Si la IA detecta que se incumplió, la llamada queda **suspendida (nota 0)**, se guarda la
nota que habría tenido y se explica qué criterio, por qué y en qué segundo. Reglas:

- **Solo cuenta lo que la rúbrica marca como crítico.** Si la IA «inventa» un crítico, se
  descarta: suspender es una decisión del jefe, no del modelo.
- **La calibración compara contra la nota sin penalizar.** El 0 es una regla, no un
  juicio; compararlo con la nota humana mediría la regla, no el desacuerdo.
- Por defecto son críticos «Disclaimers obligatorios» y «Sin afirmaciones prohibidas».
- En «a quién escuchar hoy», una suspendida sin escuchar va justo después de las
  peticiones de revisión del asesor.

### 3. Búsqueda en lo que se dijo
El listado de llamadas busca dentro de las transcripciones («cancelar», «TEA», «reclamo»)
y enseña el fragmento que coincide, resaltado. También filtra solo las suspendidas.

### 4. Motivos de llamada

La IA etiqueta **por qué llama el cliente** y el panel agrupa por ese motivo: volumen,
nota media, porcentaje en banda roja y suspendidas. El resto del panel mide al equipo;
esto mide a qué se enfrenta, que es lo que separa «control de calidad» de «inteligencia
de cliente».

Lo difícil no era detectarlo sino que no se fragmentara: a la IA se le pasa el catálogo
de motivos ya usados para que reutilice, y al guardar se normaliza y se busca un
equivalente. Así el vocabulario crece cuando el negocio cambia, pero no se duplica.

### 5. Coaching medible

Cada sesión de coaching se hace **sobre un criterio de la rúbrica** y se mide sola: la
nota de ese criterio en las llamadas del asesor 30 días antes frente a 30 días después.
Lo que se juzga es el **efecto neto**, la mejora del asesor menos la del resto del
equipo en esas mismas semanas: si todos suben, no fue la sesión. Con pocas llamadas no
hay veredicto, y la plataforma lo dice en vez de inventarlo.

Al registrarla se proponen los criterios donde el asesor más se separa del equipo, que
no son necesariamente los de nota más baja.

### 6. Criterios «no aplica»

Cualquier categoría de la rúbrica puede marcarse como «puede no aplicar», con la
condición en palabras del jefe. Si la IA decide que en esa llamada no aplica, la
categoría no puntúa y su peso se reparte entre las demás, en vez de contar como un cero.
Solo puede no aplicar lo que la rúbrica permite: la IA no se libra de una categoría por
dejarla en blanco.

## Plan: lo siguiente, por impacto

| # | Mejora | Por qué | Coste |
|---|---|---|---|
| ~~1~~ | ~~**Temas y motivos de llamada**~~ | **Hecho** (septiembre de 2026). | ✅ |
| ~~2~~ | ~~**Coaching medible**~~ | **Hecho** (septiembre de 2026). | ✅ |
| ~~3~~ | ~~**Alertas de críticos** por asesor y tendencia~~ | **Hecho** (septiembre de 2026). | ✅ |
| ~~4~~ | ~~**Preguntas «N/A» o condicionales**~~ | **Hecho** (septiembre de 2026). | ✅ |
| 5 | **Transcripción on-premise o Azure** para datos reales | Requisito de compliance antes de usar audios de clientes. | 🔴 |
| 6 | Integración con telefonía (ingesta automática) | Elimina la subida manual. | 🔴 |

---

## Fuentes

- [Zendesk — 10 best AI quality assurance software for customer service (2026)](https://www.zendesk.com/service/quality-assurance/customer-service-quality-assurance-software/)
- [Intryc — Best AI QA Software for Customer Support (2026 Buyer's Guide)](https://www.intryc.com/blog/best-ai-qa-software-for-customer-support-2026-buyers-guide)
- [Observe.AI — Auto QA](https://www.observe.ai/post-interaction/auto-qa)
- [AmplifAI — 12 Best Call Center Quality Assurance Software 2026](https://www.amplifai.com/blog/call-center-quality-assurance-software)
- [Level AI — Top 5 AI quality management software for contact centers in 2026](https://thelevel.ai/blog/top-5-ai-quality-management-software-for-contact-centers-in-2026)
- [CallMiner — Eureka](https://callminer.com/products/eureka)
- [CX Today — CallMiner Eureka review 2026](https://www.cxtoday.com/customer-analytics-intelligence/callminer-eureka-review-2026/)
- [MaestroQA — Call center quality scorecards](https://www.maestroqa.com/learning-center-articles/call-center-quality-scorecards)
- [HaddaCloud — Auditoría de llamadas automatizada: del 2 % al 100 %](https://haddacloud.com/blog/auditoria-llamadas-speech-analytics/)
- [Walter Bridge — Speech analytics para contact centers en Colombia (2026)](https://www.walterbridge.com/speech-analytics-contact-center-colombia-2026/)
