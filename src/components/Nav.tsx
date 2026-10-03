"use client";

import { BookOpen, GraduationCap, Home, Search, Shield, Target } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ICONS = { home: Home, subjects: GraduationCap, courses: Target, search: Search, admin: Shield };
export type NavItem = { href: string; label: string; icon: keyof typeof ICONS; match: string[] };

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 px-2 py-2">
      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-accent-fg">
        <BookOpen size={14} />
      </div>
      <span className="text-sm font-semibold tracking-tight">Backnote</span>
    </Link>
  );
}

function useActive(items: NavItem[]) {
  const path = usePathname();
  return (item: NavItem) =>
    item.href === "/" ? path === "/" : item.match.some((m) => path === m || path.startsWith(m + "/"));
}

export function SideNav({ items }: { items: NavItem[] }) {
  const active = useActive(items);
  return (
    <nav className="space-y-0.5">
      {items.map((n) => {
        const Icon = ICONS[n.icon];
        const on = active(n);
        return (
          <Link
            key={n.href}
            href={n.href}
            className={`flex h-8 items-center gap-2.5 rounded-md px-2.5 text-sm transition ${on ? "bg-surface-2 font-medium text-fg" : "text-muted hover:bg-surface-2/60 hover:text-fg"}`}
          >
            <Icon size={15} />
            {n.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function MobileNav({ items }: { items: NavItem[] }) {
  const active = useActive(items);
  return (
    <>
      {items.map((n) => {
        const Icon = ICONS[n.icon];
        return (
          <Link
            key={n.href}
            href={n.href}
            className={`flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm ${active(n) ? "bg-surface-2 font-medium" : "text-muted"}`}
          >
            <Icon size={14} /> {n.label}
          </Link>
        );
      })}
    </>
  );
}
