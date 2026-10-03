import type { ButtonHTMLAttributes, ReactNode } from "react";
import Link from "next/link";

export const cn = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

type Variant = "primary" | "secondary" | "ghost" | "danger";

export const buttonClass = (variant: Variant = "secondary", extra?: string) =>
  cn(
    "inline-flex h-9 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-lg px-3.5 text-sm font-medium transition-all active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 [&>svg]:shrink-0",
    variant === "primary" && "bg-accent text-accent-fg shadow-sm hover:opacity-90",
    variant === "secondary" && "border border-line bg-surface text-fg shadow-sm hover:bg-surface-2",
    variant === "ghost" && "text-muted hover:bg-surface-2 hover:text-fg",
    variant === "danger" && "text-red-fg hover:bg-red-bg",
    extra,
  );

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button className={buttonClass(variant, className)} {...props} />;
}

export function LinkButton({
  href,
  variant = "secondary",
  className,
  title,
  "aria-label": ariaLabel,
  children,
}: {
  href: string;
  variant?: Variant;
  className?: string;
  title?: string;
  "aria-label"?: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} title={title} aria-label={ariaLabel} className={buttonClass(variant, className)}>
      {children}
    </Link>
  );
}

export function Badge({ children, tone = "zinc" }: { children: ReactNode; tone?: "zinc" | "green" | "amber" | "indigo" | "red" }) {
  const tones = {
    zinc: "bg-surface-2 text-muted",
    green: "bg-green-bg text-green-fg",
    amber: "bg-amber-bg text-amber-fg",
    indigo: "bg-indigo-bg text-indigo-fg",
    red: "bg-red-bg text-red-fg",
  };
  return <span className={cn("inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium", tones[tone])}>{children}</span>;
}

export function Progress({ done, total, className }: { done: number; total: number; className?: string }) {
  const pct = total ? (done / total) * 100 : 0;
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-surface-2", className)}>
      <div className="h-full rounded-full bg-accent transition-[width] duration-700 ease-out" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("rounded-xl border border-line bg-surface shadow-[0_1px_2px_rgba(0,0,0,0.03)]", className)}>{children}</div>;
}

export function Avatar({ name }: { name: string }) {
  const letter = name.replace("@", "").trim().charAt(0).toUpperCase() || "?";
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold text-muted">{letter}</div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-8 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h2 className="text-sm font-medium">{children}</h2>
      {action}
    </div>
  );
}

export const inputClass =
  "h-9 w-full rounded-lg border border-line bg-surface px-3 text-sm outline-none transition focus:border-line-strong focus:ring-4 focus:ring-focus";
export const textareaClass =
  "w-full rounded-lg border border-line bg-surface p-3 text-sm outline-none transition focus:border-line-strong focus:ring-4 focus:ring-focus";

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-faint">{hint}</span>}
    </label>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="px-4 py-10 text-center text-sm text-faint">{children}</p>;
}
