import type { Metadata } from 'next';
import { IBM_Plex_Mono, Inter, Manrope } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

// Tipografías de marca (docs/BRAND.md). Se exponen como variables CSS para que
// globals.css y tailwind.config.ts las consuman sin acoplarse a la clase.
const manrope = Manrope({
  subsets: ['latin'],
  weight: ['500', '700', '800'],
  display: 'swap',
  variable: '--font-manrope',
});

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  display: 'swap',
  variable: '--font-inter',
});

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  display: 'swap',
  variable: '--font-plex-mono',
});

export const metadata: Metadata = {
  title: 'CallVeroQA',
  description: 'Calidad verificada en cada llamada.',
  icons: { icon: '/favicon.svg' },
};

// Script que aplica el modo claro/oscuro antes del render para evitar parpadeo.
// Por defecto = modo CLARO (paper); oscuro solo si se elige.
const themeScript = `
(function () {
  try {
    if (localStorage.getItem('callaibrate-theme') === 'dark') {
      document.documentElement.classList.add('dark');
    }
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="es"
      className={`${manrope.variable} ${inter.variable} ${plexMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
