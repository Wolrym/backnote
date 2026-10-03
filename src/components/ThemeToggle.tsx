"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const [dark, setDark] = useState(false);
  const ref = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const apply = (next: boolean) => {
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* ignore */
    }
    setDark(next);
  };

  const toggle = () => {
    const next = !dark;
    const btn = ref.current;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const doc = document as Document & { startViewTransition?: (cb: () => void) => { ready: Promise<void> } };

    if (doc.startViewTransition && btn && !reduce) {
      // Тема «розливається» колом від кнопки
      const r = btn.getBoundingClientRect();
      const x = r.left + r.width / 2;
      const y = r.top + r.height / 2;
      const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      const t = doc.startViewTransition(() => apply(next));
      t.ready.then(() => {
        document.documentElement.animate(
          { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
          { duration: 550, easing: "cubic-bezier(0.22, 1, 0.36, 1)", pseudoElement: "::view-transition-new(root)" },
        );
      });
    } else {
      const root = document.documentElement;
      root.classList.add("theme-fade");
      apply(next);
      setTimeout(() => root.classList.remove("theme-fade"), 350);
    }
  };

  return (
    <button
      ref={ref}
      onClick={toggle}
      aria-label={dark ? "Світла тема" : "Темна тема"}
      title={dark ? "Світла тема" : "Темна тема"}
      className={`relative flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-faint transition hover:bg-surface-2 hover:text-fg ${className}`}
    >
      <Sun size={15} className={`absolute transition-all duration-500 ${dark ? "rotate-0 scale-100 opacity-100" : "rotate-90 scale-0 opacity-0"}`} />
      <Moon size={15} className={`absolute transition-all duration-500 ${dark ? "-rotate-90 scale-0 opacity-0" : "rotate-0 scale-100 opacity-100"}`} />
    </button>
  );
}
