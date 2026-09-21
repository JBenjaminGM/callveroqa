---
name: CallVeroQA — Calidad verificada en cada llamada
colors:
  # --- Tokens de marca (fuente de verdad: docs/BRAND.md) ---
  ink: '#2a2420'
  ink-soft: '#6b5d52'
  paper: '#f5f1e8'
  surface: '#ffffff'
  border: '#e2d9c8'
  rust: '#b8441f'
  rust-soft: '#f0dac9'
  gold: '#a67c27'
  gold-soft: '#efe2c4'
  # --- Modo claro (tokens semánticos de la app) ---
  bg-primary: '#f5f1e8'
  bg-secondary: '#ffffff'
  bg-card: '#ffffff'
  bg-accent: '#ede7db'
  accent-primary: '#b8441f'
  accent-secondary: '#a67c27'
  text-primary: '#2a2420'
  text-secondary: '#6b5d52'
  text-muted: '#8c7f73'
  glow: 'rgba(184, 68, 31, 0.22)'
  shadow: 'rgba(42, 36, 32, 0.1)'
  # --- Modo oscuro (paleta derivada, addendum de BRAND.md) ---
  dark-bg-primary: '#1c1815'
  dark-bg-secondary: '#262019'
  dark-bg-card: '#262019'
  dark-bg-accent: '#332b23'
  dark-accent-primary: '#d95f35'
  dark-accent-secondary: '#c99b3e'
  dark-text-primary: '#f5f1e8'
  dark-text-secondary: '#b3a595'
  dark-text-muted: '#8a7d70'
  dark-border: '#3a322a'
  # --- Estado / dataviz ---
  success: '#3f7a4f'       # claro / '#5fa271' oscuro
  warning: '#a67c27'       # = gold (no hay un tercer acento)
  danger: '#a8341e'        # claro / '#d2543a' oscuro
  info: '#6b5d52'          # = ink-soft
typography:
  display:
    fontFamily: Manrope
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 1.05
  h1:
    fontFamily: Manrope
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 1.15
  h2:
    fontFamily: Manrope
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 1.2
  h3:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 1.25
  body:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 1.6
  small:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 1.5
  kpi:
    fontFamily: IBM Plex Mono
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 1
  destacado:
    fontFamily: Inter
    fontWeight: '600'
    textTransform: uppercase
    letterSpacing: 0.08em
shapes:
  radius-card: 8px       # contenedores (.rounded-card)
  radius-control: 6px    # botones, inputs, chips (.rounded-control)
  radius-round: 9999px   # solo avatares, puntos de estado y barras de progreso
spacing:
  unit: 8px
  container-max: 1280px
  gutter-desktop: 32px
  margin-desktop: 64px
  gutter-mobile: 16px
  margin-mobile: 20px
---

## Marca y estilo

El sistema de diseño implementa la identidad **CallVeroQA** bajo el tagline
**"Calidad verificada en cada llamada"**. La personalidad es **editorial y
sobria**: un lienzo cálido de papel (`paper`) con texto en tinta (`ink`), y dos únicos
acentos de marca —**rust** (#b8441f) para lo importante y **gold** (#a67c27) como
secundario—. Es el tono adecuado para una herramienta que evalúa el trabajo de
personas: seria, legible, nada estridente.

> **Fuente de verdad de la marca: [`BRAND.md`](BRAND.md).** Este documento describe
> cómo se implementa en la app. Si los dos se contradicen, manda `BRAND.md`.

> ⚠️ Las dos identidades visuales anteriores están **OBSOLETAS**. Sus colores,
> tipografías y clases de forma se describen en [`HISTORIA.md`](HISTORIA.md) y en
> ningún otro sitio: si aparece alguno en el código o en otro documento, es deuda y
> hay que corregirlo contra `BRAND.md`.

El estilo visual es **plano**: superficies sólidas con borde de 1px y sombra sutil,
radios pequeños (8px en contenedores, 6px en controles), sin glassmorphism ni
gradientes decorativos. El **modo claro es el predeterminado**; el modo oscuro es una
paleta derivada que invierte fondo y texto y aclara los acentos.

## Colores

> **Implementación canónica: `frontend/app/globals.css` + `frontend/tailwind.config.ts`.**
> Las variables CSS mandan sobre esta tabla.

La paleta se ancla en **paper** (#f5f1e8) como lienzo y **ink** (#2a2420) como texto y
como fondo del lateral de navegación. **Rust** es el acento de marca: CTA, navegación
activa, el "Vero" del wordmark, la serie principal de un gráfico y el anillo de foco.
**Gold** es el secundario y también el color de alerta.

- **Modo claro (predeterminado):** lienzo paper con tarjetas blancas de borde `#e2d9c8`.
  Hovers sobre el neutro derivado `#ede7db`.
- **Modo oscuro:** lienzo `#1c1815` y superficies `#262019`. Los acentos se aclaran
  (`rust` → `#d95f35`, `gold` → `#c99b3e`) para mantener contraste AA.
- **Barra lateral:** siempre en ink (`#2a2420` literal, no el token), en ambos modos,
  con el wordmark en negativo. Va en literal precisamente porque el token `--ink` se
  invierte en modo oscuro.

### Estado / dataviz

`success` y `danger` son **funcionales**, no decorativos: nunca se usan para branding.
Como la marca solo define dos acentos, `warning` reutiliza `gold` e `info` reutiliza
`ink-soft`.

| Estado | Claro | Oscuro | Uso |
|---|---|---|---|
| `--success` | `#3f7a4f` | `#5fa271` | Scores altos (≥ objetivo), confirmaciones |
| `--warning` | `#a67c27` | `#c99b3e` | Scores intermedios, alertas |
| `--danger` | `#a8341e` | `#d2543a` | Scores bajos / llamadas rojas, errores |
| `--info` | `#6b5d52` | `#b3a595` | Información neutra, hablante "cliente" |

## Tipografía

Tres familias, cargadas con `next/font/google` en `app/layout.tsx` y expuestas como
variables CSS (`--font-manrope`, `--font-inter`, `--font-plex-mono`).

| Familia | Pesos | Uso |
|---|---|---|
| **Manrope** | 500, 700, 800 | Titulares (`h1`–`h4`), wordmark |
| **Inter** | 400, 500, 600 | Cuerpo, UI, formularios, etiquetas |
| **IBM Plex Mono** | 400, 500, 600 | **Solo datos numéricos**: scores, IDs de llamada, marcas de tiempo, porcentajes |

Regla dura: **la mono nunca se usa en texto de interfaz**. Su función es que las cifras
queden alineadas y comparables de un vistazo, siempre con `tabular-nums`.

Los titulares van en **caso frase** (sin `text-transform`) y admiten **una** palabra
clave resaltada en rust con la clase `.hl`. Los *eyebrows* (`.destacado`) sí van en
mayúsculas, con `letter-spacing` amplio y en `text-muted`.

| Token | Tamaño / peso | Familia | Uso |
|---|---|---|---|
| `text-display` | 40px / 700 | Manrope | Hero, títulos de página |
| `text-h1` | 28px / 700 | Manrope | Títulos de sección |
| `text-h2` | 22px / 700 | Manrope | Subtítulos, cabecera |
| `text-h3` | 18px / 700 | Manrope | Títulos de tarjeta |
| `text-body` | 14px / 400 | Inter | Texto general (line-height 1.6) |
| `text-small` | 12px / 400 | Inter | Captions, labels |
| `text-kpi` | 48px / 800 | IBM Plex Mono | Números grandes del dashboard |

## Ícono y wordmark

`frontend/components/brand/logo.tsx` exporta dos piezas, y son las únicas fuentes del
logotipo en la app (no hay imágenes de marca en `public/` salvo el favicon):

- **`<Waveform />`** — 6 barras verticales con terminaciones redondeadas
  (`viewBox="0 0 72 40"`, geometría exacta de `BRAND.md`). La barra central va en
  `rust` y la última en `gold`; las demás heredan `currentColor`, de modo que el mismo
  SVG funciona sobre fondo claro y sobre el lateral oscuro.
- **`<Wordmark size="sm|md|lg" />`** — símbolo + nombre. El fragmento **"Vero" siempre en
  rust**: es lo que separa y hace legibles las tres piezas *Call · Vero · QA*.

`public/favicon.svg` repite el waveform sobre un cuadrado paper con esquinas de 14px.

## Layout y espaciado

Rejilla con base de **8px**. Ancho de contenido máximo 1280px, gutters de 32px y
márgenes de 64px en escritorio; en móvil, márgenes de 20px y gutter de 16px.

- **Barra lateral** de 240px, siempre en ink, con el wordmark arriba y el tagline abajo.
- **Tarjetas** blancas con borde de 1px sobre el lienzo paper.
- **Padding** en múltiplos de 8px.

## Elevación y profundidad

La profundidad se logra con **superficie sólida + borde tonal de 1px + `shadow-sm`**.
Nunca sombras duras, blur ni glassmorphism. La clase `.glass` se conserva por
compatibilidad, pero renderiza una superficie sólida. El único "glow" admitido es el
anillo de foco rust (`--glow`), aplicado vía `*:focus-visible`.

## Formas

| Elemento | Clase | Radio |
|---|---|---|
| Tarjetas, paneles, avisos, tooltips | `rounded-card` | 8px |
| Botones, inputs, selects, chips, badges | `rounded-control` | 6px |
| Avatares, puntos de estado, spinners, barras de progreso | `rounded-full` | círculo |

Las clases y variables de forma de la identidad anterior **ya no existen**.

## Componentes

- **CTA primario:** relleno **rust** con texto blanco, radio de 6px. Sin mayúsculas
  forzadas ni forma de píldora. El resto de botones: contorno rust (`secondary`),
  discreto (`ghost`) o `danger`.
- **Tarjetas:** superficie sólida, borde de 1px, `shadow-sm`, `rounded-card`.
- **Inputs y selects:** superficie sólida con borde tonal; el foco muestra el anillo
  rust accesible (`outline: 3px solid var(--rust)`, WCAG). El autocompletado del
  navegador se fuerza a respetar la superficie y el texto del tema.
- **Titulares con realce:** `h1`–`h4` en Manrope, caso frase, con `.hl` en la palabra
  clave (rust). Como máximo una por bloque.
- **Badges de score:** color por umbral (`danger`/`warning`/`success`), cifra en mono.
- **Transcripción sincronizada** (`components/calls/transcript-player.tsx`): el
  segmento que suena se marca con fondo `rust-soft` y borde izquierdo rust; al hacer
  clic en cualquier segmento, el audio salta a ese momento. Las marcas de tiempo van
  en mono.
- **Animaciones:** aparición suave `animate-fade-in` (respeta `prefers-reduced-motion`)
  y `skeleton` de carga con pulso sobre el borde tonal.

## Visualización de datos (dataviz)

El sistema de indicadores (`frontend/components/dashboard/viz.tsx`) mantiene el nivel
enterprise sin romper la sobriedad plana de la marca: la riqueza viene de la
**tipografía, la dataviz y el uso medido del acento**, no de sombras pesadas.

Principios aplicados:

- **Lo importante primero:** un **gauge de score** como elemento héroe, cifras grandes
  en mono con `tabular-nums`, eyebrow en mayúsculas + titular en caso frase por sección.
- **Contexto, no solo cifras:** cada KPI lleva su **delta vs periodo anterior**
  (`DeltaPill`, flecha + color semántico) y, cuando aplica, sparkline o progreso a meta.
- **Gráfico correcto por dato:** score 0-100 → anillo (`ScoreGauge`); distribución →
  donut con etiqueta central (`Donut`); evolución → área con gradiente y línea de meta
  (`CallsTrendChart`); comparación entre campañas → tabla con barras inline
  (`MiniProgress`) + delta chips; dimensiones del equipo → radar.
- **Color accesible y semántico:** `success`/`warning`/`danger` por umbral
  (`scoreVar()`); el **rust** se reserva para la serie o el dato más importante.
- **Alertas legibles:** franja de severidad a la izquierda + icono por tipo + jerarquía
  título/descripción.
- **Tooltips de marca** (`BrandTooltip`) con `rounded-card`, coherentes con el tema.

| Primitiva | Para qué |
|---|---|
| `ScoreGauge` | Score 0-100 como anillo héroe (centro con el número, color por umbral) |
| `Sparkline` | Mini-tendencia (área) dentro de un KPI |
| `Donut` | Distribución con valor/etiqueta central |
| `MiniProgress` | Barra horizontal compacta (tablas, compliance) |
| `DeltaPill` | Variación vs periodo anterior (flecha + color) |
| `BrandTooltip` | Tooltip de Recharts con el estilo de la marca |
| `StatCard` | KPI premium: label + valor + delta + sparkline/meta (`stat-card.tsx`) |
| `SectionHeader`/`Eyebrow` | Ritmo y jerarquía de secciones (`ui/section.tsx`) |
| `CallsTrendChart` | Volumen (área) + score medio (línea) + meta (`trend-chart.tsx`) |

> **Reutiliza estas primitivas** en vez de crear gráficos sueltos: todas leen las
> variables CSS (tema claro/oscuro automático) y respetan la paleta. Implementación
> canónica del color: `globals.css`.

## Tono de voz

Directo y objetivo, nunca punitivo ni robótico. La plataforma evalúa a personas reales.

**Así sí:** *"Faltó mencionar la TEA en el minuto 3. Cubrir esto sube el score en 6 puntos."*
· *"No se pudo procesar el audio. Vuelve a subirlo o revisa el formato del archivo."*

**Así no:** *"¡El asesor falló en cumplir con los requisitos obligatorios!"*
· *"Ocurrió un error inesperado. Contacte al administrador del sistema."*

Voz activa, sin disculpas en los errores, sin adjetivos de venta, y nombrando las cosas
como las entiende un asesor o un jefe de campaña, no como están construidas por dentro.
