"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Book,
  Code,
  Database,
  Cpu,
  Globe,
  Calculator,
  Terminal,
  Sparkles,
  GraduationCap,
  FlaskConical,
  Languages,
  Layers,
} from "lucide-react";
import { saveSubjectAction } from "@/app/actions";
import { Button, Field, inputClass, textareaClass } from "@/components/ui";
import type { Subject } from "@/lib/data";
import { SUBJECT_COLORS, SUBJECT_ICONS, type SubjectColorKey, type SubjectIconKey } from "@/lib/types";

export const SUBJECT_ICON_MAP = {
  book: Book,
  code: Code,
  database: Database,
  cpu: Cpu,
  globe: Globe,
  calculator: Calculator,
  terminal: Terminal,
  sparkles: Sparkles,
  "graduation-cap": GraduationCap,
  flask: FlaskConical,
  languages: Languages,
  layers: Layers,
} as const;

export default function SubjectForm({ subject, kind }: { subject?: Subject; kind: "subject" | "course" }) {
  const isSubject = kind === "subject";
  const [selectedIcon, setSelectedIcon] = useState<SubjectIconKey>(
    (subject?.icon as SubjectIconKey) || (isSubject ? "book" : "sparkles")
  );
  const [selectedColor, setSelectedColor] = useState<SubjectColorKey>(
    (subject?.color as SubjectColorKey) || "indigo"
  );

  return (
    <form action={saveSubjectAction} className="max-w-xl space-y-4">
      {subject && <input type="hidden" name="id" value={subject.id} />}
      <input type="hidden" name="kind" value={kind} />
      <input type="hidden" name="icon" value={selectedIcon} />
      <input type="hidden" name="color" value={selectedColor} />

      <Field label="Назва">
        <input name="title" required maxLength={256} defaultValue={subject?.title} className={inputClass} autoFocus />
      </Field>

      {/* Вибір іконки та акцентного кольору (Clean UI) */}
      <div className="rounded-xl border border-line bg-surface p-4 space-y-3">
        <div>
          <span className="mb-2 block text-xs font-medium text-muted">Іконка блоку</span>
          <div className="flex flex-wrap gap-2">
            {SUBJECT_ICONS.map((i) => {
              const IconComp = SUBJECT_ICON_MAP[i.key as keyof typeof SUBJECT_ICON_MAP] || Book;
              const isSel = selectedIcon === i.key;
              return (
                <button
                  key={i.key}
                  type="button"
                  title={i.label}
                  onClick={() => setSelectedIcon(i.key as SubjectIconKey)}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg border transition ${
                    isSel
                      ? "border-line-strong bg-accent text-accent-fg shadow-sm"
                      : "border-line bg-surface-2 text-muted hover:border-line-strong hover:text-fg"
                  }`}
                >
                  <IconComp size={16} />
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <span className="mb-2 block text-xs font-medium text-muted">Акцентний колір іконки</span>
          <div className="flex flex-wrap gap-2">
            {SUBJECT_COLORS.map((c) => {
              const isSel = selectedColor === c.key;
              return (
                <button
                  key={c.key}
                  type="button"
                  title={c.label}
                  onClick={() => setSelectedColor(c.key as SubjectColorKey)}
                  className={`flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-xs transition ${
                    isSel
                      ? "border-line-strong bg-surface font-medium text-fg shadow-sm ring-2 ring-focus"
                      : "border-line bg-surface text-muted hover:border-line-strong hover:text-fg"
                  }`}
                >
                  <span className={`h-2.5 w-2.5 rounded-full ${c.dot}`} />
                  {c.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {isSubject ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Код">
              <input name="code" maxLength={32} defaultValue={subject?.code ?? ""} className={inputClass} />
            </Field>
            <Field label="Кредити ECTS">
              <input name="ects" type="number" min={0} defaultValue={subject?.ects ?? ""} className={inputClass} />
            </Field>
          </div>
          <Field label="Викладач">
            <input name="instructor" maxLength={256} defaultValue={subject?.instructor ?? ""} className={inputClass} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Курс (рік навчання)">
              <input name="year" type="number" min={1} max={8} defaultValue={subject?.year ?? ""} className={inputClass} />
            </Field>
            <Field label="Семестр у році">
              <select name="term" defaultValue={subject?.term ?? ""} className={inputClass}>
                <option value="">—</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
              </select>
            </Field>
          </div>
        </>
      ) : (
        <Field label="Платформа / провайдер">
          <input name="provider" maxLength={128} defaultValue={subject?.provider ?? ""} className={inputClass} placeholder="Coursera, edX, Hugging Face…" />
        </Field>
      )}
      <Field label="Посилання">
        <input name="url" defaultValue={subject?.url ?? ""} className={inputClass} placeholder="https://…" />
      </Field>
      <Field label="Опис">
        <textarea name="description" rows={4} defaultValue={subject?.description ?? ""} className={textareaClass} />
      </Field>
      <div className="flex gap-2">
        <Button variant="primary">{subject ? "Зберегти" : "Створити"}</Button>
        <Link href={subject ? `/subjects/${subject.id}` : isSubject ? "/subjects" : "/courses"} className="inline-flex h-9 items-center px-3 text-sm text-muted hover:text-fg">
          Скасувати
        </Link>
      </div>
    </form>
  );
}
