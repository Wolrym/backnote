import { eq } from "drizzle-orm";
import { notFound, redirect } from "next/navigation";
import { db } from "@/db";
import { lessons } from "@/db/schema";
import { PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import LessonForm from "../../LessonForm";

export default async function EditLessonPage({ params }: { params: Promise<{ id: string }> }) {
  const me = await requireUser();
  const { id } = await params;
  if (!me.canEdit) redirect(`/lessons/${id}`);
  const [lesson] = await db.select().from(lessons).where(eq(lessons.id, Number(id)));
  if (!lesson) notFound();
  return (
    <div>
      <PageHeader title="Редагування заняття" subtitle={lesson.title} />
      <LessonForm subjectId={lesson.subjectId} lesson={lesson} />
    </div>
  );
}
