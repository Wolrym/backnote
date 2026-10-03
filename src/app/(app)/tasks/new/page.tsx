import { and, eq } from "drizzle-orm";
import { notFound, redirect } from "next/navigation";
import { db } from "@/db";
import { lessons } from "@/db/schema";
import { PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getSubject } from "@/lib/data";
import TaskForm from "../TaskForm";

export default async function NewTaskPage({ searchParams }: { searchParams: Promise<{ subjectId?: string; lessonId?: string }> }) {
  const me = await requireUser();
  const sp = await searchParams;
  const subject = await getSubject(Number(sp.subjectId));
  if (!subject) notFound();
  const lessonId = Number(sp.lessonId);
  const [lesson] = Number.isInteger(lessonId)
    ? await db.select().from(lessons).where(and(eq(lessons.id, lessonId), eq(lessons.subjectId, subject.id)))
    : [];
  const back = lesson ? `/lessons/${lesson.id}` : `/subjects/${subject.id}`;
  if (!me.canEdit) redirect(back);
  return (
    <div>
      <PageHeader title="Нове завдання" subtitle={lesson ? `${subject.title} · ${lesson.title}` : subject.title} />
      <TaskForm subjectId={subject.id} lessonId={lesson?.id ?? null} cancelHref={back} />
    </div>
  );
}
