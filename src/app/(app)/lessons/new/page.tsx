import { notFound, redirect } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getSubject } from "@/lib/data";
import LessonForm from "../LessonForm";

export default async function NewLessonPage({ searchParams }: { searchParams: Promise<{ subjectId?: string }> }) {
  const me = await requireUser();
  const { subjectId } = await searchParams;
  const subject = await getSubject(Number(subjectId));
  if (!subject) notFound();
  if (!me.canEdit) redirect(`/subjects/${subject.id}`);
  return (
    <div>
      <PageHeader title="Нове заняття" subtitle={subject.title} />
      <LessonForm subjectId={subject.id} />
    </div>
  );
}
