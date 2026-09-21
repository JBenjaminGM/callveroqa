import { cn } from '@/lib/utils';

/**
 * Marca CallVeroQA (docs/BRAND.md).
 *
 * El símbolo son 6 barras verticales tipo waveform: comunica "señal de voz" sin
 * recurrir al cliché del ícono de teléfono. La barra central va en `rust` y hay
 * un acento menor en `gold`; las demás heredan `currentColor`, para que el mismo
 * SVG sirva sobre fondo claro y sobre el lateral oscuro sin duplicarlo.
 */
export function Waveform({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 72 40"
      fill="none"
      role="img"
      aria-label="CallVeroQA"
      className={cn('h-5 w-auto', className)}
    >
      <rect x="0" y="16" width="8" height="8" rx="4" fill="currentColor" />
      <rect x="13" y="10" width="8" height="20" rx="4" fill="currentColor" />
      <rect x="26" y="2" width="8" height="36" rx="4" fill="var(--rust)" />
      <rect x="39" y="10" width="8" height="20" rx="4" fill="currentColor" />
      <rect x="52" y="14" width="8" height="12" rx="4" fill="currentColor" />
      <rect x="64" y="17" width="8" height="6" rx="3" fill="var(--gold)" />
    </svg>
  );
}

const WORDMARK_SIZES = {
  sm: { mark: 'h-4', text: 'text-[15px]' },
  md: { mark: 'h-5', text: 'text-[19px]' },
  lg: { mark: 'h-7', text: 'text-[26px]' },
} as const;

/**
 * Lockup completo: símbolo + nombre. El fragmento "Vero" siempre va en `rust`,
 * que es lo que separa y hace legibles las tres piezas: Call · Vero · QA.
 */
export function Wordmark({
  size = 'md',
  className,
}: {
  size?: keyof typeof WORDMARK_SIZES;
  className?: string;
}) {
  const { mark, text } = WORDMARK_SIZES[size];
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <Waveform className={mark} />
      <span
        className={cn('font-heading font-extrabold tracking-tight', text)}
      >
        Call<span className="text-rust">Vero</span>QA
      </span>
    </span>
  );
}
