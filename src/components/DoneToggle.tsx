"use client";

import { Check } from "lucide-react";
import { useOptimistic, useTransition } from "react";
import { toggleDoneAction } from "@/app/actions";

export default function DoneToggle({ lessonId, done, variant = "circle" }: { lessonId: number; done: boolean; variant?: "circle" | "button" }) {
  const [optimistic, setOptimistic] = useOptimistic(done);
  const [, start] = useTransition();

  const toggle = () =>
    start(async () => {
      setOptimistic(!optimistic);
      await toggleDoneAction(lessonId, !optimistic);
    });

  if (variant === "button") {
    return (
      <button
        onClick={toggle}
        className={`inline-flex h-9 shrink-0 cursor-pointer items-center gap-2 rounded-lg px-3.5 text-sm font-medium shadow-sm transition-all active:scale-[0.97] ${
          optimistic ? "border border-line bg-surface text-fg hover:bg-surface-2" : "bg-accent text-accent-fg hover:opacity-90"
        }`}
      >
        <Check size={14} /> {optimistic ? "Пройдено" : "Позначити"}
      </button>
    );
  }

  return (
    <button
      onClick={toggle}
      aria-label={optimistic ? "Зняти позначку" : "Позначити пройденим"}
      className={`flex h-5 w-5 shrink-0 cursor-pointer items-center justify-center rounded-full border transition-all active:scale-90 ${
        optimistic ? "border-accent bg-accent text-accent-fg" : "border-line-strong hover:border-muted"
      }`}
    >
      {optimistic && (
        <span className="pop">
          <Check size={12} strokeWidth={3} />
        </span>
      )}
    </button>
  );
}
