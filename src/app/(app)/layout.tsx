import { LogOut } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { logoutAction } from "@/app/actions";
import { Avatar } from "@/components/ui";
import { Logo, MobileNav, SideNav, type NavItem } from "@/components/Nav";
import ThemeToggle from "@/components/ThemeToggle";
import { requireUser } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function AppLayout({ children }: { children: ReactNode }) {
  const me = await requireUser();

  const items: NavItem[] = [
    { href: "/", label: "Огляд", icon: "home", match: [] },
    { href: "/subjects", label: "Предмети", icon: "subjects", match: ["/subjects"] },
    { href: "/courses", label: "Курси", icon: "courses", match: ["/courses"] },
    { href: "/search", label: "Пошук", icon: "search", match: ["/search"] },
    ...(me.isAdmin ? [{ href: "/admin", label: "Учасники", icon: "admin", match: ["/admin"] } satisfies NavItem] : []),
  ];

  return (
    <div className="min-h-screen md:flex">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-line bg-surface/60 p-3 md:sticky md:top-0 md:flex md:h-screen">
        <div className="mb-4 flex items-center justify-between pr-1">
          <Logo />
          <ThemeToggle />
        </div>
        <SideNav items={items} />
        <div className="mt-auto flex items-center gap-2.5 rounded-lg p-2">
          <Link href="/account" className="flex min-w-0 flex-1 items-center gap-2.5" title="Мій акаунт">
            <Avatar name={me.fullName} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{me.fullName}</div>
              <div className="truncate text-xs text-faint">{me.isAdmin ? "Адмін" : me.canEdit ? "Редактор" : "Перегляд"}</div>
            </div>
          </Link>
          <form action={logoutAction}>
            <button aria-label="Вийти" title="Вийти" className="cursor-pointer rounded-md p-1.5 text-faint transition hover:bg-surface-2 hover:text-fg">
              <LogOut size={15} />
            </button>
          </form>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex items-center gap-1 overflow-x-auto border-b border-line bg-surface/85 px-3 py-2 backdrop-blur md:hidden">
        <MobileNav items={items} />
        <div className="ml-auto flex shrink-0 items-center">
          <ThemeToggle />
          <form action={logoutAction}>
            <button aria-label="Вийти" className="cursor-pointer p-1.5 text-faint">
              <LogOut size={15} />
            </button>
          </form>
        </div>
      </header>

      <main className="min-w-0 flex-1">
        <div className="rise mx-auto w-full max-w-4xl px-5 py-8 md:px-8 md:py-10">{children}</div>
      </main>
    </div>
  );
}
