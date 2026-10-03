import { Search } from "lucide-react";
import Link from "next/link";
import { TaskIcon } from "@/components/Attachments";
import { Badge, Card, Empty, PageHeader, SectionTitle } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { search } from "@/lib/data";
import { LESSON_KIND_LABEL, TASK_KIND_LABEL } from "@/lib/types";

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  await requireUser();
  const q = ((await searchParams).q ?? "").trim().slice(0, 100);
  const r = q.length >= 2 ? await search(q) : null;
  const empty = r && !r.subjects.length && !r.lessons.length && !r.tasks.length;

  return (
    <div className="w-full">
      <PageHeader title="Пошук" subtitle="Предмети, заняття, конспекти й завдання" />
      <form className="relative mb-8">
        <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
        <input
          name="q"
          defaultValue={q}
          autoFocus
          placeholder="Що шукаємо?"
          className="h-10 w-full rounded-lg border border-line bg-surface pl-9 pr-3 text-sm outline-none transition focus:border-line-strong focus:ring-4 focus:ring-focus"
        />
      </form>

      {empty && (
        <Card>
          <Empty>Нічого не знайдено</Empty>
        </Card>
      )}

      {r && r.subjects.length > 0 && (
        <section className="mb-6">
          <SectionTitle>Предмети й курси</SectionTitle>
          <Card className="divide-y divide-line overflow-hidden">
            {r.subjects.map((s) => (
              <Link key={s.id} href={`/subjects/${s.id}`} className="flex items-center gap-3 px-4 py-3 text-sm transition hover:bg-surface-2/60">
                <span className="min-w-0 flex-1 truncate font-medium">{s.title}</span>
                <Badge>{s.kind === "course" ? "Курс" : "Предмет"}</Badge>
              </Link>
            ))}
          </Card>
        </section>
      )}

      {r && r.lessons.length > 0 && (
        <section className="mb-6">
          <SectionTitle>Заняття</SectionTitle>
          <Card className="divide-y divide-line overflow-hidden">
            {r.lessons.map(({ lesson: l, subjectTitle }) => (
              <Link key={l.id} href={`/lessons/${l.id}`} className="block px-4 py-3 transition hover:bg-surface-2/60">
                <div className="truncate text-sm font-medium">{l.title}</div>
                <div className="mt-0.5 text-xs text-faint">
                  {LESSON_KIND_LABEL[l.kind]} {l.number} · {subjectTitle}
                </div>
              </Link>
            ))}
          </Card>
        </section>
      )}

      {r && r.tasks.length > 0 && (
        <section>
          <SectionTitle>Завдання</SectionTitle>
          <Card className="divide-y divide-line overflow-hidden">
            {r.tasks.map((t) => (
              <Link key={t.id} href={`/tasks/${t.id}`} className="flex items-center gap-3 px-4 py-3 transition hover:bg-surface-2/60">
                <span className="text-faint">
                  <TaskIcon kind={t.kind} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{t.title}</div>
                  <div className="text-xs text-faint">{t.subjectTitle}</div>
                </div>
                <Badge>{TASK_KIND_LABEL[t.kind]}</Badge>
              </Link>
            ))}
          </Card>
        </section>
      )}
    </div>
  );
}
