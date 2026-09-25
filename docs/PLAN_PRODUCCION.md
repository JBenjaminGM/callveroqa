# Plan para pasar de "funciona" a "se puede vender"

> Septiembre de 2026. La plataforma **funciona y está desplegada**; esto es lo que
> falta para que un cliente de verdad la use y pague por ella. Cada punto dice **qué
> bloquea**, **qué cuesta** y **quién lo puede hacer**. Lo que depende de una tarjeta de
> crédito o de una cuenta externa está separado a propósito: no es código.
>
> Estado: ✅ hecho · 🔧 en curso · ⬜ pendiente · 💳 requiere decisión de gasto

---

## 1. Bloqueantes de venta (sin esto, un cliente no puede operar)

| # | Qué | Por qué bloquea | Estado |
|---|---|---|---|
| 1.1 | **Gestión de usuarios en la UI** (crear, desactivar, cambiar rol) | Hoy solo se crean asesores desde la ficha del ejecutivo. Un cliente no puede dar de alta a su equipo sin tocar la base de datos. | ✅ |
| 1.2 | **Cambio de contraseña** por el propio usuario | Las contraseñas las genera el seed y se imprimen una vez. Nadie puede cambiarlas. Es inaceptable para un banco. | ✅ |
| 1.3 | **Reseteo de contraseña por un administrador** | Sin correo saliente, alguien tiene que poder devolver el acceso a quien lo pierda. | ✅ |
| 1.4 | **Almacenamiento de audios persistente (S3)** | En Render el disco es efímero: cada despliegue borra las grabaciones y las llamadas ya subidas dejan de poder reproducirse. Verificado en vivo. | ✅ código · 💳 cuenta |
| 1.5 | **Retención y borrado de datos** | Un banco exige poder decir «los audios se borran a los N días» y borrar los datos de una persona a petición. | ✅ |
| 1.6 | **Base de datos que no caduque** | El PostgreSQL gratuito de Render se borra a los 30 días. Ya pasó una vez y se perdieron los datos. | 💳 |

## 2. Confianza y operación (sin esto se vende, pero se cae)

| # | Qué | Estado |
|---|---|---|
| 2.1 | Copia de seguridad diaria verificada (workflow existente + secreto `DATABASE_URL`) | ⬜ 💳 |
| 2.2 | `/health` que compruebe también la base de datos, no solo que el proceso vive | ✅ |
| 2.3 | Identificador de petición en los logs para poder rastrear un error concreto | ✅ |
| 2.4 | Página de error y estado de la API para el usuario final (cold start del plan gratis) | ✅ ya existía |
| 2.5 | Monitorización de errores (Sentry o similar) | ⬜ 💳 |

## 3. Producto: lo que hace que elijan esto y no a la competencia

Detalle y comparativa en [`COMPETENCIA.md`](COMPETENCIA.md).

| # | Qué | Valor | Estado |
|---|---|---|---|
| 3.1 | **Alerta propia de criterio crítico** + tasa de suspendidas por campaña | Riesgo normativo visible de un vistazo; hoy se confunde con «banda roja». | ✅ |
| 3.2 | **Temas y motivos de llamada** (por qué llama el cliente, no solo cómo lo hizo el asesor) | Es el salto de «QA» a «inteligencia de cliente». Lo que venden CallMiner y Level AI. | ✅ |
| 3.3 | **Coaching medible**: sesión ligada a un criterio, con antes/después | Cierra el ciclo con datos; lo piden todas las guías de compra. | ✅ |
| 3.4 | Criterios «no aplica» en la rúbrica | Un criterio que no aplica no debería bajar la nota. | ⬜ |
| 3.5 | Multi-cliente (una instalación, varias empresas) | Necesario para vender como SaaS a varios clientes; **no** para vender una instalación a un banco. | ⬜ |

## 4. Lo que no es código (lo tiene que hacer el dueño)

| # | Qué | Por qué |
|---|---|---|
| 4.1 | 💳 Plan de pago de Render (base de datos que no caduque + disco o S3) | ~7 USD/mes la base; sin esto los datos tienen fecha de caducidad. |
| 4.2 | 💳 Cuenta de S3 (o equivalente) y sus claves | Para que las grabaciones sobrevivan a un despliegue. |
| 4.3 | 🔑 `GROQ_API_KEY` válida en Render | Sin ella no se transcribe ni analiza nada nuevo. |
| 4.4 | 📄 Aviso de privacidad y contrato de tratamiento de datos | Ver [`COMPLIANCE_CHECKLIST.md`](COMPLIANCE_CHECKLIST.md): el audio sale a un tercero (Groq, EE. UU.). Para datos reales de clientes hace falta transcripción on-premise o Azure, y el visto bueno de Compliance. |
| 4.5 | 🏷️ Dominio propio (p. ej. `app.callveroqa.com`) | `*.vercel.app` y `*.onrender.com` no se presentan a un banco. |

## 5. Orden recomendado

1. **Hecho ya:** todo lo marcado ✅ en las secciones 1, 2 y 3 (incluidos 3.2, los motivos de llamada, y 3.3, el coaching medible).
2. **Esta semana:** 4.1 y 4.2 (gasto pequeño) + 2.1 y 2.5. Con eso la plataforma deja de
   tener fecha de caducidad y se entera uno cuando algo falla.
3. **Antes de enseñarla a un cliente real:** 4.4 y 4.5.
4. **Siguiente versión de producto:** 3.2 y 3.3, que son las dos que se notan en una demo
   frente a la competencia.
5. **Solo si se vende a más de un cliente:** 3.5 (multi-cliente).
