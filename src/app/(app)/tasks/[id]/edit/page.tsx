import { notFound, redirect } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getTaskBundle } from "@/lib/data";
import TaskForm from "../../TaskForm";

export default async function EditTaskPage({ params }: { params: Promise<{ id: string }> }) {
  const me = await requireUser();
  const { id } = await params;
  if (!me.canEdit) redirect(`/tasks/${id}`);
  const b = Number.isInteger(Number(id)) ? await getTaskBundle(Number(id), me.id) : null;
  if (!b) notFound();
  const { task } = b;
  return (
    <div>
      <PageHeader title="Редагування завдання" subtitle="Зміна базової версії не стирає особисті копії користувачів" />
      <TaskForm subjectId={task.subjectId} lessonId={task.lessonId} cancelHref={`/tasks/${task.id}`} initial={task} />
    </div>
  );
}
