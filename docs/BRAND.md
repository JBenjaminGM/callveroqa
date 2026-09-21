# CallVeroQA — Guía de marca

> Fuente de verdad de la marca. Reemplaza toda referencia a las identidades
> anteriores, que están retiradas y solo se describen en
> [`HISTORIA.md`](HISTORIA.md).

## Nombre y concepto

**CallVeroQA** — tres piezas que se leen solas: *Call* (la llamada), *Vero*
(del latín *verus*, "verdadero": lo que se comprueba es cierto) y *QA* (Quality
Assurance, el término que ya usa cualquier call center). Dice qué es el producto
sin explicar un juego de palabras: **verificar la calidad de cada llamada**.
Sustituye a CallAIbrate (septiembre de 2026), cuyo juego *Call · AI · Calibrate*
había que explicar. La función de **calibración** (acuerdo IA-humano) conserva su
nombre: es un concepto de QA, no de marca.

**Tagline:** "Calidad verificada en cada llamada."

En texto, el nombre siempre se escribe `CallVeroQA` (C, V, Q y A en mayúsculas,
todo junto). En UI, el fragmento "Vero" se resalta en el color de acento (`rust`)
y el resto en el color de texto principal: así se separan visualmente las tres
piezas.

## Color

| Token | Hex | Uso |
|---|---|---|
| `ink` | `#2A2420` | Texto principal |
| `ink-soft` | `#6B5D52` | Texto secundario |
| `paper` | `#F5F1E8` | Fondo general |
| `surface` | `#FFFFFF` | Tarjetas, superficies |
| `border` | `#E2D9C8` | Divisores, bordes |
| `rust` | `#B8441F` | Acento de marca, CTA, "Vero" del wordmark |
| `rust-soft` | `#F0DAC9` | Fondos de badges/hover sobre rust |
| `gold` | `#A67C27` | Acento secundario, estado de alerta |
| `gold-soft` | `#EFE2C4` | Fondos de badges sobre gold |
| `success` | `#3F7A4F` | Cumple / score alto |
| `danger` | `#A8341E` | Incumplimiento / score bajo |

`rust` y `gold` son los únicos dos acentos de marca. `success`/`danger` son
colores funcionales (estado), no decorativos.

## Tipografía

| Fuente | Pesos | Uso |
|---|---|---|
| Manrope | 500, 700, 800 | Títulos, headers de sección |
| Inter | 400, 500, 600 | Cuerpo, UI, formularios |
| IBM Plex Mono | 400, 500, 600 | Scores, IDs de llamada, timestamps — solo datos numéricos |

Cargar vía next/font/google en app/layout.tsx.

## Forma y detalles

- Radio de borde: 8px en cards, 6px en botones/inputs.
- Sombras sutiles únicamente. Nunca sombras duras.
- Sin glassmorphism, sin gradientes decorativos.
- Iconografía: mantener lucide-react, color por defecto ink-soft.

## Ícono / wordmark

SVG de 6 barras verticales tipo waveform, alturas variables, terminaciones
redondeadas. Una barra central en rust, el resto en ink, un acento menor en gold.

```svg
<svg width="72" height="40" viewBox="0 0 72 40" fill="none">
  <rect x="0"  y="16" width="8" height="8"  rx="4" fill="#2A2420"/>
  <rect x="13" y="10" width="8" height="20" rx="4" fill="#2A2420"/>
  <rect x="26" y="2"  width="8" height="36" rx="4" fill="#B8441F"/>
  <rect x="39" y="10" width="8" height="20" rx="4" fill="#2A2420"/>
  <rect x="52" y="14" width="8" height="12" rx="4" fill="#2A2420"/>
  <rect x="64" y="17" width="8" height="6"  rx="3" fill="#A67C27"/>
</svg>
```

## Tono de voz

Directo y objetivo, nunca punitivo ni robótico.

Así sí:
- "Faltó mencionar la TEA en el minuto 3. Cubrir esto sube el score en 6 puntos."
- "No se pudo procesar el audio. Vuelve a subirlo o revisa el formato del archivo."

Así no:
- "¡El asesor falló en cumplir con los requisitos obligatorios de la campaña!"
- "Ocurrió un error inesperado. Contacte al administrador del sistema."

## Tokens Tailwind

```js
colors: {
  ink:         '#2A2420',
  'ink-soft':  '#6B5D52',
  paper:       '#F5F1E8',
  surface:     '#FFFFFF',
  border:      '#E2D9C8',
  rust:        '#B8441F',
  'rust-soft': '#F0DAC9',
  gold:        '#A67C27',
  'gold-soft': '#EFE2C4',
  success:     '#3F7A4F',
  danger:      '#A8341E',
}
```

---

## Addendum — extensiones acordadas

Todo lo anterior es la guía original. Esta sección cubre los casos que la app real
necesita y que la guía no fija, para que siga habiendo **una sola** fuente de verdad.

### Modo oscuro (derivado)

La aplicación conserva el conmutador claro/oscuro. La paleta oscura se deriva de los
tokens base: se invierten fondo y texto, y se aclaran los acentos para mantener
contraste AA sobre fondo oscuro. La jerarquía y el papel de cada token no cambian.

| Token | Claro | Oscuro |
|---|---|---|
| `paper` (fondo) | `#F5F1E8` | `#1C1815` |
| `surface` | `#FFFFFF` | `#262019` |
| `border` | `#E2D9C8` | `#3A322A` |
| `ink` (texto) | `#2A2420` | `#F5F1E8` |
| `ink-soft` | `#6B5D52` | `#B3A595` |
| `rust` | `#B8441F` | `#D95F35` |
| `rust-soft` | `#F0DAC9` | `#4A2418` |
| `gold` | `#A67C27` | `#C99B3E` |
| `gold-soft` | `#EFE2C4` | `#423418` |
| `success` | `#3F7A4F` | `#5FA271` |
| `danger` | `#A8341E` | `#D2543A` |

### Neutros derivados

Necesarios para superficies sutiles que no son ni fondo ni borde. No son acentos de
marca y nunca se usan para destacar nada.

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| `bg-accent` | `#EDE7DB` | `#332B23` | Hovers, pistas de barras de progreso, chips neutros |
| `text-muted` | `#8C7F73` | `#8A7D70` | Texto terciario (etiquetas, marcas de tiempo) |

Los estados que la guía no nombra se mapean a tokens existentes, sin inventar color:
`warning` = `gold`, `info` = `ink-soft`.

### Titulares

Sin `text-transform`: los títulos se escriben en caso frase, con Manrope 700.
Se conserva el dispositivo de resalte `<span class="hl">` para **una** palabra clave
por titular, pintada en `rust`. Uso moderado: como máximo una por bloque.

Las etiquetas superiores (*eyebrows*) sí van en mayúsculas, con `letter-spacing`
amplio y en `ink-soft`.

### Radios

| Elemento | Radio |
|---|---|
| Cards, contenedores, tooltips | `8px` (`rounded-card`) |
| Botones, inputs, selects, chips | `6px` (`rounded-control`) |
| Avatares, puntos de estado, spinners | círculo (`rounded-full`) |
