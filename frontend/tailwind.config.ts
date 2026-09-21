import type { Config } from 'tailwindcss';

/**
 * Configuración de Tailwind para CallVeroQA.
 *
 * Los tokens semánticos (bg-*, text-*, accent-*) se mapean a variables CSS
 * definidas en app/globals.css, lo que permite el cambio de modo claro/oscuro
 * sin recompilar. Los tokens de marca (ink, paper, rust, gold…) también son
 * variables, para que respeten el modo oscuro derivado de docs/BRAND.md.
 */
const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  future: {
    // Compila `hover:` dentro de `@media (hover: hover)`. En una pantalla táctil
    // el hover se queda pegado tras el toque; así deja de ocurrir en toda la
    // aplicación de una vez, sin envolver cada regla a mano.
    hoverOnlyWhenSupported: true,
  },
  theme: {
    extend: {
      colors: {
        bg: {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          card: 'var(--bg-card)',
          accent: 'var(--bg-accent)',
        },
        accent: {
          primary: 'var(--accent-primary)',
          secondary: 'var(--accent-secondary)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        border: 'var(--border)',
        success: 'var(--success)',
        warning: 'var(--warning)',
        danger: 'var(--danger)',
        info: 'var(--info)',
        // Tokens de marca CallVeroQA (docs/BRAND.md).
        ink: 'var(--ink)',
        'ink-soft': 'var(--ink-soft)',
        paper: 'var(--paper)',
        surface: 'var(--surface)',
        rust: 'var(--rust)',
        'rust-soft': 'var(--rust-soft)',
        gold: 'var(--gold)',
        'gold-soft': 'var(--gold-soft)',
      },
      fontFamily: {
        // Inter = cuerpo y UI; Manrope = titulares; IBM Plex Mono = solo datos.
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        heading: ['var(--font-manrope)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-plex-mono)', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Titulares en Manrope Bold (700); el KPI usa el peso máximo (800).
        display: ['40px', { lineHeight: '1.05', fontWeight: '700' }],
        h1: ['28px', { lineHeight: '1.15', fontWeight: '700' }],
        h2: ['22px', { lineHeight: '1.2', fontWeight: '700' }],
        h3: ['18px', { lineHeight: '1.25', fontWeight: '700' }],
        body: ['14px', { lineHeight: '1.6', fontWeight: '400' }],
        small: ['12px', { lineHeight: '1.5', fontWeight: '400' }],
        kpi: ['48px', { lineHeight: '1', fontWeight: '800' }],
      },
      borderRadius: {
        // 8px en contenedores, 6px en controles (docs/BRAND.md).
        card: '8px',
        control: '6px',
      },
      // Movimiento: las mismas curvas y duraciones que globals.css, para poder
      // escribir `duration-ui ease-out-strong` en vez de números sueltos.
      transitionTimingFunction: {
        'out-strong': 'var(--ease-out)',
        'in-out-strong': 'var(--ease-in-out)',
      },
      transitionDuration: {
        press: 'var(--duration-press)',
        ui: 'var(--duration-ui)',
        reveal: 'var(--duration-reveal)',
      },
    },
  },
  plugins: [],
};

export default config;
