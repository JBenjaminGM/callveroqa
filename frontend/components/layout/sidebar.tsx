'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Phone,
  Users,
  Megaphone,
  Settings,
  UploadCloud,
  Gauge,
  Scale,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { isManager, useAuthStore } from '@/lib/auth';
import { Wordmark } from '@/components/brand/logo';

// Navegación para roles de gestión (admin / jefe).
const MANAGER_NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/calls', label: 'Llamadas', icon: Phone },
  { href: '/calls/new', label: 'Nueva llamada', icon: UploadCloud },
  { href: '/calibracion', label: 'Calibración', icon: Scale },
  { href: '/agents', label: 'Ejecutivos', icon: Users },
  { href: '/campaigns', label: 'Campañas', icon: Megaphone },
  { href: '/settings', label: 'Configuración', icon: Settings },
];

// Navegación del asesor (solo su rendimiento y sus llamadas).
const ASESOR_NAV = [
  { href: '/mi-panel', label: 'Mi rendimiento', icon: Gauge },
  { href: '/calls', label: 'Mis llamadas', icon: Phone },
];

/**
 * Barra lateral de navegación: lienzo Ink con el wordmark en negativo.
 *
 * Los colores van en literal y no como `bg-ink`/`text-paper` porque el lateral
 * debe permanecer oscuro también en modo oscuro, donde esos tokens se invierten.
 */
export function Sidebar() {
  const pathname = usePathname();
  const user = useAuthStore((s) => s.user);
  const navItems = isManager(user) ? MANAGER_NAV : ASESOR_NAV;

  return (
    <aside className="flex w-60 shrink-0 flex-col bg-[#2a2420] p-3 text-paper">
      {/* Lockup de marca. El "Vero" va en Rust; el resto hereda el color del texto. */}
      <div className="mb-6 px-2 pt-4 text-[#f5f1e8]">
        <Wordmark size="md" />
      </div>

      <nav className="flex flex-col gap-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active =
            href === '/calls'
              ? pathname === '/calls'
              : pathname === href ||
                (href !== '/dashboard' &&
                  href !== '/calls/new' &&
                  pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-control px-3 py-2.5 text-body transition-colors',
                active
                  ? 'bg-[#b8441f] font-semibold text-white'
                  : 'text-[#f5f1e8]/70 hover:bg-white/10 hover:text-[#f5f1e8]',
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      <p className="mt-auto px-3 pb-2 text-[11px] leading-snug text-[#f5f1e8]/45">
        Calidad verificada en cada llamada.
      </p>
    </aside>
  );
}
