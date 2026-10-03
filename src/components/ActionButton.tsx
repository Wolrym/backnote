"use client";

import { useTransition, type ReactNode } from "react";
import { buttonClass } from "@/components/ui";

/** Кнопка, що викликає server action (передається як bound-функція), з необов'язковим підтвердженням. */
export default function ActionButton({
  action,
  confirm,
  variant = "ghost",
  className,
  children,
  label,
}: {
  action: () => Promise<unknown>;
  confirm?: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  className?: string;
  children: ReactNode;
  label?: string;
}) {
  const [pending, start] = useTransition();
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={pending}
      className={buttonClass(variant, className)}
      onClick={() => {
        if (confirm && !window.confirm(confirm)) return;
        start(async () => {
          await action();
        });
      }}
    >
      {children}
    </button>
  );
}
