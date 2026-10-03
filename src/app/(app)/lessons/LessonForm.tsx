import Link from "next/link";
import { saveLessonAction } from "@/app/actions";
import { Button, Field, inputClass, textareaClass } from "@/components/ui";
import type { Lesson } from "@/lib/data";
import { LESSON_KIND_LABEL } from "@/lib/types";

export default function LessonForm({ subjectId, lesson }: { subjectId: number; lesson?: Lesson }) {
  return (
    <form action={saveLessonAction} className="max-w-xl space-y-4">
      {lesson && <input type="hidden" name="id" value={lesson.id} />}
      <input type="hidden" name="subjectId" value={subjectId} />
      <div className="grid gap-3 sm:grid-cols-[1fr_9rem]">
        <Field label="Назва">
          <input name="title" required maxLength={256} defaultValue={lesson?.title} className={inputClass} autoFocus />
        </Field>
        <Field label="Тип">
          <select name="kind" defaultValue={lesson?.kind ?? "lecture"} className={inputClass}>
            {Object.entries(LESSON_KIND_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Дата">
          <input name="heldOn" type="date" defaultValue={lesson?.heldOn ?? ""} className={inputClass} />
        </Field>
        <Field label="Відео (YouTube або інше посилання)">
          <input name="videoUrl" defaultValue={lesson?.videoUrl ?? ""} className={inputClass} placeholder="https://…" />
        </Field>
      </div>
      <Field label="Опис">
        <textarea name="description" rows={3} defaultValue={lesson?.description ?? ""} className={textareaClass} />
      </Field>
      <Field label="Конспект (Markdown)" hint="Таблиці, чекліст, код і формули $...$ підтримуються">
        <textarea name="summary" rows={12} defaultValue={lesson?.summary ?? ""} className={`${textareaClass} font-mono text-[13px]`} />
      </Field>
      <div className="flex gap-2">
        <Button variant="primary">{lesson ? "Зберегти" : "Створити"}</Button>
        <Link href={lesson ? `/lessons/${lesson.id}` : `/subjects/${subjectId}`} className="inline-flex h-9 items-center px-3 text-sm text-muted hover:text-fg">
          Скасувати
        </Link>
      </div>
    </form>
  );
}
