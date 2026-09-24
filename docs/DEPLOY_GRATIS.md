# 🚀 Publicar CallVeroQA gratis (Vercel + Render + Groq)

Guía para dejar la plataforma **accesible desde cualquier ordenador**, **sin pagar nada**.

**Arquitectura del despliegue gratis:**

```
Navegador ─▶ Frontend (Vercel, gratis) ─▶ API (Render, gratis) ─▶ PostgreSQL (Render, gratis)
                                                  │
                                                  └─▶ Groq (transcripción + análisis, gratis)
```

> Sin worker Celery ni Redis: la API procesa cada llamada **dentro de sí misma**
> (`PROCESS_INLINE=true`, vía `BackgroundTasks`), que es lo que permite caber en el
> plan gratis.

**Antes de empezar necesitas:** (1) el repo ya en GitHub —ya lo tienes:
`JBenjaminGM/callveroqa`—, (2) tu **API key de Groq** (`gsk_...`, gratis en
console.groq.com), (3) una cuenta de **Render** y otra de **Vercel** (ambas se
crean gratis con tu GitHub, sin tarjeta).

---

## 1) Backend + base de datos → Render

1. Entra a **https://render.com** → **Get Started** → inicia sesión con **GitHub**.
2. Arriba: **New → Blueprint**.
3. Conecta tu repositorio **`JBenjaminGM/callveroqa`**. Render leerá el archivo
   `render.yaml` y te mostrará que va a crear: **callveroqa-api** (web) y **callveroqa-db**
   (PostgreSQL), ambos *Free*. Pulsa **Apply**.
4. Configura las variables de entorno del servicio **callveroqa-api**:
   - **GROQ_API_KEY** = tu clave `gsk_...`
   - **CORS_ORIGINS** = `https://callveroqa.vercel.app` (la URL exacta de tu
     frontend en Vercel, sin barra final; si aún no la tienes, pon `*` y la afinas
     en el paso 3).
   - **PROCESS_INLINE** = `true` (procesa sin worker, vía `BackgroundTasks`).
   - **GROQ_API_KEY**, **JWT_SECRET** y demás secretos los pide Render al aplicar
     el blueprint; `DATABASE_URL` lo inyecta solo.
5. Espera ~5 min a que construya y despliegue. Cuando esté *Live*, copia la URL
   del servicio, será algo como **`https://callveroqa-api.onrender.com`**.
6. Comprueba que vive: abre **`https://callveroqa-api.onrender.com/health`** → debe
   responder `{"status":"healthy"}`.

---

## 2) Frontend → Vercel

1. Entra a **https://vercel.com** → **Sign Up** con **GitHub**.
2. **Add New → Project** → importa **`JBenjaminGM/callveroqa`**.
3. ⚠️ **Root Directory:** pulsa *Edit* y selecciona **`frontend`** (¡importante,
   el frontend está en esa subcarpeta!).
4. Despliega **Environment Variables** y añade:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://callveroqa-api.onrender.com/api/v1`  *(tu URL de Render + `/api/v1`)*
5. Pulsa **Deploy**. En ~2 min tendrás una URL como **`https://callveroqa.vercel.app`**.

---

## 3) Conectarlos (CORS) y listo

1. Vuelve a **Render → callveroqa-api → Environment**.
2. Confirma que **CORS_ORIGINS** es tu URL exacta de Vercel
   (`https://callveroqa.vercel.app`, sin barra final). Guarda → se redepliega solo.
3. Abre tu **URL de Vercel** y entra con una de las cuentas sembradas:
   - **admin:** `admin@callveroqa.com`
   - **jefe:** `jefe@callveroqa.com`
   - **asesor:** el email del ejecutivo (p. ej. `maria@banco.com`)

   Las contraseñas las genera el *seed* al azar y las imprime **una sola vez** en los
   logs del servicio (Render → `callveroqa-api` → **Logs**, en el primer arranque). Para
   fijarlas tú, define `SEED_ADMIN_PASSWORD`, `SEED_JEFE_PASSWORD` y
   `SEED_ASESOR_PASSWORD` en las variables de entorno antes del primer despliegue.

🎉 ¡Ya está online y accesible desde cualquier PC, gratis!

---

## ⚠️ Cosas que debes saber (del plan gratis)

- **Cold-start (se "duerme"):** si nadie la usa por ~15 min, la API de Render se
  apaga. La **primera carga** después tarda **~50 segundos** en despertar (puede
  verse como un "error de API" momentáneo; luego va normal). Está mitigado por dos
  lados:
  - **Keepalive:** la GitHub Action `.github/workflows/keepalive.yml` hace ping a
    `/health` cada 12 min para mantener despierto el servicio.
  - **Resiliencia en el frontend:** `frontend/lib/api.ts` usa timeout de 90 s,
    reintenta en el arranque en frío y muestra el mensaje "activando el servidor".
  - Aun así, para una demo conviene abrir la web 1 min antes para "calentarla".
- **Base de datos gratis caduca ~90 días** en Render. Cuando avise, la recreas, o
  cambias a **Neon** (neon.tech, gratis y no caduca): crea una BD, copia su
  *connection string* y ponla en Render como `DATABASE_URL`.
- **Audios efímeros:** los archivos de audio no se conservan tras reinicios (el
  disco gratis no es persistente). No afecta al análisis (transcripción y scores
  se guardan en la BD); solo significa que *reintentar* una llamada vieja podría
  no encontrar su audio.
- **Gobernanza:** es una **vista previa para evaluación**. Cambia la contraseña del
  admin y no subas datos reales de clientes sin la aprobación previa de Compliance
  (el audio se procesa en Groq, EE. UU.).
- **Coste total: $0.**

---

## 🔁 Actualizaciones

Cada vez que hagas `git push` a `main`, **Render y Vercel redepliegan solos**.
No tienes que hacer nada más.
