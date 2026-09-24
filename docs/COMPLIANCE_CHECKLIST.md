# Checklist de Compliance, DPO y Seguridad

> **Qué es esto.** La lista de comprobaciones que deben quedar cerradas **antes** de
> usar CallVeroQA con grabaciones reales de clientes de un banco. Hoy la plataforma
> es funcional pero **no está aprobada** para ese uso.
>
> Cada ítem lleva responsable y la evidencia que hay que archivar. Un ítem sin
> evidencia archivada cuenta como no cerrado.

**Estado actual:** ningún bloque aprobado. La plataforma opera como entorno de
evaluación (cabecera `X-Prototype-Notice`, logs con `environment="evaluation"`).

---

## 1. Base legal y protección de datos

| | Comprobación | Responsable | Evidencia |
|---|---|---|---|
| [ ] | Base de licitud del tratamiento identificada y documentada (contrato, interés legítimo o consentimiento) | DPO | Registro de actividades de tratamiento |
| [ ] | Finalidad declarada limitada a evaluación de calidad; prohibido el uso secundario | DPO | Política interna firmada |
| [ ] | Aviso de grabación verificado en el guion de la llamada y en la locución inicial | Compliance | Guion aprobado |
| [ ] | Información al titular sobre el análisis automatizado de la grabación | DPO | Texto de la política de privacidad |
| [~] | Plazo de conservación definido para audio, transcripción y análisis, y **borrado automático** implementado al vencer | DPO + Ingeniería | **Implementado para el audio** (Ajustes → Retención de grabaciones, `retention_audio_days`; purga automática cada 6 h y botón «Aplicar ahora» que devuelve cuántas borró). **Falta que el DPO fije el plazo** y decidir si transcripción y análisis también caducan: hoy se conservan a propósito, porque son la evaluación y no la voz. |
| [~] | Procedimiento de atención de derechos ARCO/ARSULIPO (acceso, rectificación, supresión, oposición) sobre los datos de la plataforma | DPO | **Supresión implementada**: `DELETE /agents/{id}/data` (solo administradores) borra llamadas, audios, transcripciones, análisis y revisiones de una persona, y devuelve el recuento para el registro. **Falta el procedimiento documentado** (quién lo atiende, en qué plazo y cómo se acredita al solicitante). |
| [ ] | Evaluación de impacto (DPIA/EIPD) completada y aprobada | DPO | Informe de EIPD |

## 2. Datos personales dentro del contenido

| | Comprobación | Responsable | Evidencia |
|---|---|---|---|
| [ ] | Entendido y aceptado que el enmascarado (`masking_service`) es **best-effort** por patrones: no garantiza eliminar toda la PII | Compliance | Acta de aceptación de riesgo |
| [ ] | Verificado qué se persiste **sin** enmascarar: el **audio original** y, según el flujo, la transcripción completa | Ingeniería | Inventario de datos |
| [ ] | Cifrado en reposo del almacenamiento de audios y de la base de datos | Seguridad | Configuración del proveedor |
| [ ] | Cifrado en tránsito (HTTPS) forzado en frontend y API, sin fallback a HTTP | Seguridad | Configuración TLS |
| [ ] | Muestreo manual de transcripciones para medir la tasa real de fuga de PII | DPO | Informe de muestreo |
| [ ] | El **audio original sin enmascarar** se almacena tal cual y se envía completo a Groq. Evaluar si es aceptable o si hay que procesar en infraestructura propia | DPO | Análisis de riesgo |

## 3. Subencargados de tratamiento

La transcripción y el análisis se envían a proveedores externos. Cada uno es un
subencargado y necesita su propia verificación.

| | Proveedor | Qué recibe | Comprobación | Evidencia |
|---|---|---|---|---|
| [ ] | **Groq** | Audio completo (Whisper) y transcripción (Llama) | DPA firmado, política de retención cero o acotada, ubicación de procesamiento | Contrato + política del proveedor |
| [ ] | **Render** | Base de datos y audios | DPA, región de alojamiento, cifrado en reposo | Contrato |
| [ ] | **Vercel** | Solo frontend (sin datos de llamada) | DPA, confirmación de que no procesa contenido | Contrato |
| [ ] | — | Transferencias internacionales de datos evaluadas (cláusulas contractuales tipo si aplica) | DPO | Análisis de transferencia |
| [ ] | — | Alternativa evaluada de procesamiento en infraestructura propia o en región concreta (el backend ya soporta Azure vía `AI_PROVIDER`) | Arquitectura | Análisis comparativo |

## 4. Seguridad técnica

| | Comprobación | Responsable | Evidencia |
|---|---|---|---|
| [ ] | `JWT_SECRET` largo, aleatorio y distinto por entorno; rotación documentada | Seguridad | Gestor de secretos |
| [ ] | Expiración de tokens revisada (hoy `JWT_EXPIRE_HOURS=8`) y política de cierre de sesión | Seguridad | Configuración |
| [ ] | Rate limiting activo en autenticación y subida de audios | Seguridad | Configuración de `slowapi` |
| [ ] | Control de acceso por rol verificado con pruebas: un asesor no accede a datos de otros | Seguridad | Suite de tests de roles |
| [ ] | **Almacenamiento persistente y cifrado** para los audios. ⚠️ Hoy el almacenamiento local en Render es **efímero**: se pierde en cada redespliegue | Ingeniería | Configuración de S3 o disco persistente |
| [~] | Copias de seguridad de la base de datos, con restauración probada | Ingeniería | Existe el workflow `.github/workflows/backup-db.yml` (volcado diario con `pg_dump`, artefacto a 30 días). **Falta** definir el secreto `DATABASE_URL` y **probar una restauración real**. |
| [ ] | Los dumps de respaldo contienen **transcripciones completas**, es decir datos personales. Definir dónde viven, quién accede y cuánto se conservan | DPO | Política de retención de copias |
| [ ] | Registro de auditoría de accesos: quién escuchó o descargó qué grabación y cuándo | Seguridad | Diseño e implementación del log |
| [ ] | Gestión de altas y bajas de usuarios ligada a RR. HH. | Seguridad | Procedimiento |
| [ ] | Pentest o revisión de seguridad externa sobre la aplicación desplegada | Seguridad | Informe de pentest |

## 5. Uso laboral y evaluación de personas

La plataforma puntúa el desempeño de trabajadores identificables. Eso añade
obligaciones que van más allá de la protección de datos.

| | Comprobación | Responsable | Evidencia |
|---|---|---|---|
| [ ] | Los asesores están informados de que sus llamadas se evalúan con IA, y de con qué criterios | RR. HH. | Comunicación firmada |
| [ ] | Revisión humana obligatoria antes de cualquier consecuencia laboral: el score **no** decide por sí solo | RR. HH. | Política de evaluación |
| [ ] | Canal de impugnación de una evaluación concreta | RR. HH. | Procedimiento |
| [ ] | Análisis de sesgo del modelo (acento, género, dialecto) sobre una muestra representativa | Calidad + DPO | Informe de sesgo |
| [ ] | Rúbrica y umbrales de QA revisados y aprobados por el negocio | Calidad | Acta de aprobación |
| [ ] | Consulta a la representación de los trabajadores, si aplica | RR. HH. | Acta |

## 6. Incidentes conocidos

| | Incidente | Estado | Nota |
|---|---|---|---|
| [x] | Una `GROQ_API_KEY` real se commiteó a `backend/.env.example` (commit `aeda304`, junio 2026) | **Cerrado** | La clave fue **revocada** (verificado: la API de Groq responde 401). Sigue en el historial de git del repositorio privado; no se reescribe porque la clave está muerta y hacerlo rompería todos los clones. El espejo público (`callqa`) se genera con historial propio a partir de un estado en el que la clave ya no estaba. **No reutilizar nunca esa clave.** |
| [x] | Contraseñas de demostración fijas en el código y publicadas en el README (`Admin123!`, `Jefe123!`, `Asesor123!`) | **Cerrado** | El seed genera contraseñas aleatorias y las muestra una sola vez. Además **rota** cualquier cuenta sembrada que todavía use una de las contraseñas publicadas. |
| [ ] | Auditoría de si esas contraseñas se usaron en algún entorno accesible desde internet | Pendiente | Revisar logs de acceso del despliegue en Render |
| [x] | **Pérdida total de los datos de producción** (sept. 2026): la PostgreSQL del plan gratuito de Render caducó a los 30 días y fue eliminada con todo su contenido. No existía ninguna copia de seguridad | **Cerrado sin recuperación** | Los datos eran de un entorno de evaluación, no de clientes reales. Se recreó la base y se añadió `.github/workflows/backup-db.yml`. Ver `RENOMBRADO_INFRA.md`. |

## 7. Puertas de salida a producción

Ninguna grabación real entra en la plataforma hasta que estas tres firmas existan.

| | Aprobación | Responsable | Evidencia |
|---|---|---|---|
| [ ] | Compliance aprueba el uso con datos reales | Compliance | Acta firmada |
| [ ] | El DPO aprueba el tratamiento y la EIPD | DPO | Acta firmada |
| [ ] | Seguridad aprueba la arquitectura desplegada | Seguridad | Acta firmada |
| [ ] | Retirada de las salvaguardas de entorno de evaluación (`X-Prototype-Notice`, `environment="evaluation"`) solo tras las tres firmas | Ingeniería | Commit de retirada |
