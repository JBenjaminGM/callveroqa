'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

/**
 * Toggle de modo claro/oscuro.
 *
 * Persiste la elección en localStorage y aplica la clase `.dark` al <html>.
 * La transición de colores (200ms) la define globals.css.
 */
export function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
  }, []);

  function toggle() {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('callveroqa-theme', next ? 'dark' : 'light');
  }

  return (
    <button
      onClick={toggle}
      aria-label="Cambiar modo claro/oscuro"
      className="flex h-10 w-10 items-center justify-center rounded-control
                 text-text-primary transition-colors hover:bg-bg-accent/40"
    >
      {isDark ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}
