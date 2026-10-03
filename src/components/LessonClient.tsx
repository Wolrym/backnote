"use client";

import { Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { saveNoteAction } from "@/app/actions";

/** YouTube: легка мініатюра, плеєр завантажується лише після кліку. */
export function VideoEmbed({ id }: { id: string }) {
  const [play, setPlay] = useState(false);
  return (
    <div className="relative mt-5 aspect-video w-full overflow-hidden rounded-xl border border-line bg-surface-2">
      {play ? (
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1`}
          title="Запис заняття"
          allow="accelerometer; autoplay; encrypted-media; picture-in-picture; fullscreen"
          allowFullScreen
          className="absolute inset-0 h-full w-full"
        />
      ) : (
        <button onClick={() => setPlay(true)} className="group absolute inset-0 cursor-pointer" aria-label="Відтворити відео">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`https://i.ytimg.com/vi/${id}/hqdefault.jpg`} alt="" loading="lazy" className="h-full w-full object-cover opacity-90 transition group-hover:opacity-100" />
          <span className="absolute left-1/2 top-1/2 flex h-14 w-14 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-accent text-accent-fg shadow-lg transition group-hover:scale-105">
            <Play size={20} fill="currentColor" />
          </span>
        </button>
      )}
    </div>
  );
}

/** Приватні нотатки з автозбереженням. */
export function NoteEditor({ lessonId, initial }: { lessonId: number; initial: string }) {
  const [text, setText] = useState(initial);
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const last = useRef(initial);

  useEffect(() => {
    if (text === last.current) return;
    setState("saving");
    const t = setTimeout(async () => {
      await saveNoteAction(lessonId, text);
      last.current = text;
      setState("saved");
    }, 700);
    return () => clearTimeout(t);
  }, [text, lessonId]);

  return (
    <section className="mt-8">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium">Мої нотатки</h2>
        <span className="text-xs text-faint">{state === "saving" ? "Зберігаю…" : state === "saved" ? "Збережено" : ""}</span>
      </div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={5}
        placeholder="Приватні нотатки бачиш лише ти…"
        className="w-full resize-y rounded-xl border border-line bg-surface p-4 text-sm outline-none transition focus:border-line-strong focus:ring-4 focus:ring-focus"
      />
    </section>
  );
}
