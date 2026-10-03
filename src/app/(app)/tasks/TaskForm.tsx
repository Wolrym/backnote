"use client";

import { Loader2, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState, useTransition } from "react";
import { saveTaskAction } from "@/app/actions";
import { Button, Field, inputClass, textareaClass } from "@/components/ui";

type Initial = { id?: number; title: string; kind: string; content: string; fileName: string | null };

const MAX_BYTES = 15_000_000; // 15 МБ

const detect = (name: string): string | null => {
  const ext = name.toLowerCase().split(".").pop();
  if (ext === "html" || ext === "htm") return "html";
  if (ext === "py") return "python";
  if (ext === "md" || ext === "markdown" || ext === "txt") return "markdown";
  return null;
};

export default function TaskForm({
  subjectId,
  lessonId,
  initial,
  cancelHref,
}: {
  subjectId: number;
  lessonId: number | null;
  initial?: Initial;
  cancelHref: string;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [kind, setKind] = useState(initial?.kind ?? "markdown");
  const [content, setContent] = useState(initial?.content ?? "");
  const [fileName, setFileName] = useState(initial?.fileName ?? "");
  const [error, setError] = useState("");
  const [isReadingFile, setIsReadingFile] = useState(false);
  const [isSubmitting, startTransition] = useTransition();
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    if (file.size > MAX_BYTES) {
      setError(`Файл завеликий: ${(file.size / 1024 / 1024).toFixed(1)} МБ (максимум 15 МБ)`);
      return;
    }
    setError("");
    setIsReadingFile(true);
    try {
      const text = await file.text();
      setContent(text);
      setFileName(file.name);
      const k = detect(file.name);
      if (k) setKind(k);
      if (!title) setTitle(file.name.replace(/\.[^.]+$/, ""));
    } catch {
      setError("Не вдалося прочитати вміст файлу");
    } finally {
      setIsReadingFile(false);
    }
  };

  const isBusy = isReadingFile || isSubmitting;

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (isBusy) return;
    const formData = new FormData(e.currentTarget);
    startTransition(async () => {
      try {
        await saveTaskAction(formData);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Помилка збереження завдання");
      }
    });
  };

  return (
    <form onSubmit={handleSubmit} className="relative max-w-2xl space-y-4">
      {/* Оверлей блокування та візуальний показник збереження/читання */}
      {isBusy && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bg/70 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-line bg-surface p-6 shadow-xl">
            <Loader2 className="h-8 w-8 animate-spin text-accent" />
            <div className="text-sm font-medium">
              {isReadingFile ? "Зчитуємо файл у браузері…" : "Зберігаємо завдання на сервері…"}
            </div>
            <div className="text-xs text-muted">Будь ласка, зачекайте, не закривайте сторінку</div>
          </div>
        </div>
      )}

      {initial?.id && <input type="hidden" name="id" value={initial.id} />}
      <input type="hidden" name="subjectId" value={subjectId} />
      {lessonId && <input type="hidden" name="lessonId" value={lessonId} />}
      <input type="hidden" name="fileName" value={fileName} />

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!isBusy) onFile(e.dataTransfer.files[0]);
        }}
        onClick={() => !isBusy && fileRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center gap-1.5 rounded-xl border border-dashed border-line-strong bg-surface px-4 py-6 text-center transition ${
          isBusy ? "pointer-events-none opacity-50" : "hover:bg-surface-2/60"
        }`}
      >
        {isReadingFile ? <Loader2 size={20} className="animate-spin text-accent" /> : <Upload size={20} className="text-faint" />}
        <span className="text-sm font-medium">
          {isReadingFile ? "Зчитую файл..." : "Завантаж файл завдання"}
        </span>
        <span className="text-xs text-muted">.html · .py · .md — перетягни сюди або натисни. Підтримуються файли до 15 МБ.</span>
        {fileName && <span className="mt-1 rounded-md bg-surface-2 px-2 py-0.5 font-mono text-xs">{fileName}</span>}
        <input ref={fileRef} type="file" accept=".html,.htm,.py,.md,.markdown,.txt" hidden disabled={isBusy} onChange={(e) => onFile(e.target.files?.[0])} />
      </div>

      <div className="grid gap-3 sm:grid-cols-[1fr_10rem]">
        <Field label="Назва">
          <input
            name="title"
            required
            maxLength={256}
            disabled={isBusy}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className={inputClass}
          />
        </Field>
        <Field label="Тип">
          <select name="kind" value={kind} disabled={isBusy} onChange={(e) => setKind(e.target.value)} className={inputClass}>
            <option value="markdown">Markdown</option>
            <option value="python">Python</option>
            <option value="html">HTML-сторінка</option>
          </select>
        </Field>
      </div>

      <Field
        label="Вміст"
        hint={
          kind === "html"
            ? "Повна HTML-сторінка з тестом чи вправами — відобразиться на сайті в ізольованому вікні"
            : kind === "python"
              ? "Код, який користувач зможе змінити й запустити"
              : "Текст завдання"
        }
      >
        <textarea
          name="content"
          required
          rows={16}
          disabled={isBusy}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Tab" && !e.shiftKey) {
              e.preventDefault();
              const el = e.currentTarget;
              const { selectionStart: s, selectionEnd: end } = el;
              const next = content.slice(0, s) + "    " + content.slice(end);
              setContent(next);
              requestAnimationFrame(() => {
                el.setSelectionRange(s + 4, s + 4);
              });
            }
          }}
          spellCheck={false}
          className={`${textareaClass} font-mono text-[13px]`}
        />
      </Field>

      {error && <p className="rounded-lg bg-red-bg px-3 py-2 text-xs text-red-fg">{error}</p>}
      <div className="flex gap-2">
        <Button variant="primary" disabled={isBusy}>
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="animate-spin" /> Зберігаю…
            </>
          ) : initial?.id ? (
            "Зберегти"
          ) : (
            "Додати завдання"
          )}
        </Button>
        <Link href={cancelHref} className={`inline-flex h-9 items-center px-3 text-sm text-muted hover:text-fg ${isBusy ? "pointer-events-none opacity-50" : ""}`}>
          Скасувати
        </Link>
      </div>
    </form>
  );
}
