# Lo que tiene que hacer el dueño para terminar

> 25 de septiembre de 2026. Todo lo que se podía resolver con código está hecho y
> desplegado. Lo que queda necesita **una cuenta, una tarjeta o un permiso** que solo
> tienes tú. Está ordenado por urgencia; cada paso dice dónde hacer clic, qué valor
> poner, cómo comprobar que ha funcionado y qué avisarme para cerrarlo por mi lado.
>
> Nada de esto requiere tocar código. Donde hace falta un cambio en el repositorio,
> lo hago yo cuando me avises.

---

## Resumen

| # | Qué | Por qué | Coste | Urgencia |
|---|---|---|---|---|
| 1 | Pasar la base de datos de Render a un plan de pago | La gratuita **se borra con todo dentro** a los 30 días | ~7 USD/mes | 🔴 antes de ~8 oct |
| 2 | Conceder el permiso `workflow` a GitHub | Sin él no puedo arreglar las copias de seguridad, que **nunca han funcionado** | 0 | 🔴 |
| 3 | Crear la frase de cifrado de las copias | El repositorio es público: sin cifrar, cualquiera podría bajarse las copias | 0 | 🔴 con el 2 |
| 4 | Poner una `GROQ_API_KEY` válida en Render | Sin ella no se analiza ninguna llamada nueva | 0 | 🟠 |
| 5 | Hacer privado el repositorio completo | Hoy es público con toda la documentación interna | 0 | 🟠 |
| 6 | Cuenta de S3 para los audios | Cada despliegue borra las grabaciones subidas | ~1 USD/mes | 🟠 |
| 7 | Monitorización de errores (Sentry) | Enterarte de un fallo antes que el cliente | 0 (plan gratis) | 🟡 |
| 8 | Dominio propio | `*.onrender.com` y `*.vercel.app` no se presentan a un banco | ~10-15 USD/año | 🟡 antes de enseñarla |
| 9 | Aviso de privacidad y visto bueno de Compliance | Obligatorio antes de usar llamadas reales | — | 🟡 antes de datos reales |

---

## 1. Base de datos de pago en Render 🔴

**Por qué es lo primero:** la PostgreSQL del plan gratuito se elimina a los 30 días de
crearse. La actual se recreó hacia el **8 de septiembre**, así que caduca hacia el
**8 de octubre** (Render muestra la fecha exacta en el panel y avisa por correo). Ya pasó
una vez y se perdió todo.

1. Entra en <https://dashboard.render.com> y abre la base **`callaibrate-db`**.
2. Busca la opción para cambiar de plan (*Upgrade* / *Change plan*) y elige el plan de
   pago más pequeño (Basic). Es suficiente para varios miles de llamadas.
3. Confirma. **No se pierden datos:** se cambia el plan de la misma base.

**Cómo comprobarlo:** en el panel, la base ya no muestra fecha de caducidad.

**Avísame** con el nombre exacto del plan que elegiste: tengo que ponerlo en
`render.yaml` (hoy dice `plan: free`), para que una sincronización del blueprint no
intente volver al plan gratuito.

---

## 2. Permiso `workflow` en GitHub 🔴

**Por qué:** la copia de seguridad diaria **ha fallado todos los días**. El secreto
`DATABASE_URL` está bien puesto, pero el runner usa `pg_dump` 16 y la base de Render es
la 18, así que aborta por diferencia de versión. El arreglo está hecho, pero vive en
`.github/workflows/`, y el token con el que trabajo no puede modificar esa carpeta.

1. En una terminal (la de VS Code o PowerShell) ejecuta:
   ```
   gh auth refresh -h github.com -s workflow
   ```
2. Te enseña un **código de 8 caracteres** y te pide abrir
   <https://github.com/login/device>. Ábrelo, pega el código y pulsa **Authorize**.
3. La terminal dirá `Authentication complete`.

**Avísame** y subo el arreglo (rama `infra/backup-cifrado`), lanzo la copia a mano y
compruebo que termina en verde.

> Alternativa sin darme el permiso: puedo explicarte el cambio para que lo pegues tú en
> el editor web de GitHub. Es más lento y más fácil equivocarse.

---

## 3. Frase de cifrado de las copias 🔴 (junto con el 2)

**Por qué:** el repositorio es público, y en un repositorio público cualquier usuario
con cuenta de GitHub puede descargar los artefactos de los workflows. Las copias llevan
transcripciones de llamadas. Por eso el arreglo **cifra la copia antes de subirla** y,
si falta la frase, **se niega a subirla sin cifrar**.

1. Genera una frase larga y aleatoria (32 caracteres o más) con tu gestor de
   contraseñas. **Guárdala en él**: sin ella, las copias no se pueden restaurar.
2. En GitHub: repositorio `callveroqa` → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**.
3. Nombre: `BACKUP_PASSPHRASE`. Valor: la frase. **Add secret**.

**Cómo restaurar una copia** (cuando haga falta; necesitas `gpg` y `pg_restore`):

```
gpg --decrypt callaibrate-AAAAMMDD-HHMM.dump.gpg > copia.dump
pg_restore --no-owner --no-privileges -d "<URL de la base destino>" copia.dump
```

---

## 4. `GROQ_API_KEY` válida en Render 🟠

**Por qué:** es la clave de la IA que transcribe y evalúa. Sin una válida, cualquier
llamada nueva termina en error. No puedo comprobar desde fuera si la actual funciona,
porque la cuenta demo no puede subir llamadas.

1. Entra en <https://console.groq.com> → **API Keys** → **Create API Key**. Copia la
   clave (empieza por `gsk_`); solo se muestra una vez.
2. En Render: servicio **`callaibrate-api`** → **Environment** → variable
   `GROQ_API_KEY` → pega la clave → **Save changes**. Render redespliega solo (2-4 min).
3. **Opcional, para probar en local:** pégala también en `backend/.env`
   (`GROQ_API_KEY=gsk_...`). Ese archivo no se sube nunca al repositorio.

**Cómo comprobarlo:** entra como administrador, sube un audio en **Nueva llamada** y
espera a que pase de «Analizando» a una nota. Si falla, el detalle de la llamada dice
por qué.

**Avísame** y hago la prueba que falta de «no aplica» con la IA real: una llamada de
consulta (sin venta ni objeciones) tiene que salir con esas dos categorías en «no
aplica» y nota en el resto.

---

## 5. Hacer privado el repositorio completo 🟠

**Por qué:** `JBenjaminGM/callveroqa` es **público** y contiene toda la documentación
interna, los scripts de operación y el historial. La idea original era que fuera
privado y que lo público fuera el espejo limpio `callveroqa-public`.

**Antes de hacerlo, una consecuencia:** en un repositorio privado, GitHub Actions solo
da 2.000 minutos gratis al mes. El *keepalive* (un ping cada 12 minutos para que Render
no duerma el backend) gasta más que eso él solo. Así que primero hay que sustituirlo:

1. Crea una cuenta gratuita en <https://uptimerobot.com> → **Add New Monitor** →
   tipo **HTTP(s)** → URL `https://callaibrate-api.onrender.com/health` → intervalo
   **5 minutos** → pon tu correo en las alertas → **Create Monitor**. Además de
   mantenerlo despierto, te avisa por correo si se cae.
2. **Avísame**: desactivo el workflow `keepalive.yml` (necesita el permiso del paso 2).
3. Después: GitHub → repositorio `callveroqa` → **Settings** → **General** → al final,
   **Danger Zone** → **Change visibility** → **Make private** → confirma.
4. Comprueba que Render y Vercel siguen desplegando: haz cualquier cambio pequeño o
   pídemelo a mí, y mira que ambos paneles muestran un despliegue nuevo. Si alguno
   falla por permisos, en GitHub → **Settings** → **Applications** → su app →
   **Configure** → dale acceso al repositorio `callveroqa`.

> Si prefieres dejarlo público, las copias van cifradas igualmente (paso 3), pero la
> documentación interna seguirá a la vista.

---

## 6. Almacenamiento S3 para los audios 🟠

**Por qué:** hoy los audios se guardan en el disco del servidor de Render, que **se
vacía en cada despliegue**. Las llamadas de la demo ya se reponen solas en cada
arranque, pero cualquier audio que suba un cliente se perdería al siguiente despliegue.

1. Crea una cuenta en <https://aws.amazon.com> si no la tienes.
2. **S3** → **Create bucket**:
   - Nombre: por ejemplo `callveroqa-audios-produccion` (tiene que ser único en el mundo).
   - Región: `sa-east-1` (São Paulo) o `us-east-1`. Apunta la que elijas.
   - **Block all public access: activado** (viene así por defecto; no lo cambies).
   - **Create bucket**.
3. **IAM** → **Users** → **Create user** → nombre `callveroqa-api` → sin acceso a la
   consola → **Next** → **Attach policies directly** → **Create policy** → pestaña
   **JSON** y pega esto, cambiando el nombre del bucket:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
       "Resource": "arn:aws:s3:::callveroqa-audios-produccion/audios/*"
     }]
   }
   ```
   Guárdala como `callveroqa-audios`, vuelve al usuario, adjúntala y créalo. Así la
   clave solo puede tocar los audios, y nada más de tu cuenta de AWS.
4. Abre el usuario → **Security credentials** → **Create access key** → uso
   *Application running outside AWS* → copia la **Access key** y la **Secret access
   key** (la secreta solo se ve una vez).
5. En Render: **`callaibrate-api`** → **Environment** → añade o cambia:

   | Variable | Valor |
   |---|---|
   | `STORAGE_PROVIDER` | `s3` |
   | `AWS_S3_BUCKET` | el nombre del bucket |
   | `AWS_REGION` | la región del paso 2 |
   | `AWS_ACCESS_KEY_ID` | la access key |
   | `AWS_SECRET_ACCESS_KEY` | la secret key |

   **Save changes**. Si falta alguna, la API se niega a arrancar y el log dice cuál:
   es a propósito, para no perder el primer audio.

**Cómo comprobarlo:** en S3 aparecerá la carpeta `audios/` con los 6 audios de la demo
(se suben solos al arrancar). Abre cualquier llamada de la demo y dale a reproducir.

**Avísame:** pongo `render.yaml` con `STORAGE_PROVIDER` en modo panel, para que una
sincronización del blueprint no lo devuelva a `local`.

---

## 7. Monitorización de errores (Sentry) 🟡

El código ya está listo y **apagado** hasta que exista la variable. Nunca envía datos
personales: ni cuerpos de petición, ni el token, ni variables internas (un test lo
comprueba).

1. Crea una cuenta gratuita en <https://sentry.io> (plan *Developer*).
2. **Create Project** → plataforma **FastAPI** → nombre `callveroqa-api` → **Create**.
3. Copia el **DSN** que te enseña (`https://...@....ingest.sentry.io/...`). Si lo
   pierdes: *Project Settings* → *Client Keys (DSN)*.
4. En Render: **`callaibrate-api`** → **Environment** → `SENTRY_DSN` = el DSN →
   **Save changes**.

**Cómo comprobarlo:** en los logs de Render, al arrancar, aparece `Sentry activo`.
Cada error tendrá una etiqueta `request_id`, el mismo que ve el usuario en el mensaje de
error y que aparece en los logs.

---

## 8. Dominio propio 🟡

**Por qué:** presentar `callaibrate-api.onrender.com` a un banco no transmite confianza,
y además lleva el nombre anterior del producto. **Recomiendo esto en lugar de renombrar
los servicios** de Render y Vercel: con dominio propio, los nombres internos no los ve
nadie.

1. Compra el dominio (por ejemplo `callveroqa.com`) en Cloudflare, Namecheap o donde
   prefieras.
2. **Frontend** — Vercel → proyecto → **Settings** → **Domains** → añade
   `app.callveroqa.com` → Vercel te dice qué registro crear (normalmente un `CNAME`
   de `app` a `cname.vercel-dns.com`) → créalo en tu proveedor de dominio.
3. **Backend** — Render → **`callaibrate-api`** → **Settings** → **Custom Domains** →
   añade `api.callveroqa.com` → crea el `CNAME` de `api` a
   `callaibrate-api.onrender.com`.
4. Espera a que ambos paneles muestren el dominio verificado y con certificado.
5. Variables:
   - Render → `CORS_ORIGINS` = `https://app.callveroqa.com,https://callaibrate.vercel.app`
     (las dos, mientras conviven).
   - Vercel → **Settings** → **Environment Variables** → `NEXT_PUBLIC_API_URL` =
     `https://api.callveroqa.com/api/v1` → y después **Redeploy** del último despliegue
     (esta variable se incrusta al compilar).

**Avísame:** actualizo el keepalive, la documentación y el README con las URLs nuevas y
lo verifico de punta a punta.

> La rama `infra/renombrar-servicios` (sin subir) queda obsoleta si se va por el
> dominio: cambiar el nombre de un servicio en Render no cambia su URL `.onrender.com`,
> y ese cambio en `render.yaml` crearía servicios nuevos. Si aun así quieres renombrar,
> dímelo antes y lo repasamos juntos.

---

## 9. Antes de usar llamadas reales de clientes 🟡

No es técnico, pero bloquea la venta a un banco. Está detallado en
[`COMPLIANCE_CHECKLIST.md`](COMPLIANCE_CHECKLIST.md). Lo mínimo:

- **Aviso de privacidad y contrato de encargado de tratamiento** con el cliente.
- **El audio sale a un tercero** (Groq, en EE. UU.). Para datos reales, lo habitual es
  pedir transcripción en Azure (región del cliente) u on-premise. En el código es
  configuración (`WHISPER_PROVIDER` / `AI_PROVIDER`), pero necesita su cuenta y su
  contrato.
- **Visto bueno de Compliance / DPO** del banco.
- Definir la **retención de grabaciones** en Configuración (por defecto no caducan).

---

## Lo que haré yo cuando me avises

| Cuando hagas… | Yo hago… |
|---|---|
| 1 (plan de pago) | Poner el plan en `render.yaml` y verificar que la base responde. |
| 2 + 3 (permiso + frase) | Subir el arreglo de las copias, lanzarla a mano y comprobar que sale un `.dump.gpg`. |
| 4 (clave de Groq) | Probar «no aplica» con la IA real y dejarlo documentado. |
| 5 (UptimeRobot) | Desactivar el keepalive de GitHub. |
| 6 (S3) | Ajustar `render.yaml` y comprobar que los audios están en S3 y se oyen. |
| 8 (dominio) | Actualizar keepalive, documentación y README, y verificarlo de punta a punta. |

Para publicar el espejo limpio `callveroqa-public` con todo lo nuevo, basta con
decírmelo (es una publicación en un repositorio público, así que no la hago sin que me
lo pidas).
