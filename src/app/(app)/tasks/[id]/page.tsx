import { ChevronLeft, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { deleteTaskAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { TaskIcon } from "@/components/Attachments";
import TaskWorkspace from "@/components/TaskWorkspace";
import { Badge, LinkButton } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getTaskBundle } from "@/lib/data";
import { getAppSettings } from "@/lib/settings";
import { TASK_KIND_LABEL } from "@/lib/types";

const EXT = { html: "html", markdown: "md", python: "py" } as const;

export default async function TaskPage({ params }: { params: Promise<{ id: string }> }) {
  const me = await requireUser();
  const { id: raw } = await params;
  const id = Number(raw);
  const b = Number.isInteger(id) ? await getTaskBundle(id, me.id) : null;
  if (!b) notFound();
  const { task, subject, lesson, work } = b;
  const kind = task.kind as "html" | "markdown" | "python";
  const backHref = lesson ? `/lessons/${lesson.id}` : `/subjects/${subject.id}`;
  const fileName = task.fileName || `${task.title.replace(/[^\p{L}\p{N}_-]+/gu, "_")}.${EXT[kind]}`;

  const settings = getAppSettings();

  return (
    <div>
      <Link href={backHref} className="mb-4 inline-flex items-center gap-1 text-sm text-muted transition hover:text-fg">
        <ChevronLeft size={15} /> {lesson ? lesson.title : subject.title}
      </Link>

      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <Badge>
              <TaskIcon kind={kind} size={11} /> {TASK_KIND_LABEL[kind]}
            </Badge>
            <span className="truncate text-xs text-faint">{subject.title}</span>
          </div>
          <h1 className="mt-2.5 text-2xl font-semibold tracking-tight">{task.title}</h1>
        </div>
        {me.canEdit && (
          <div className="flex shrink-0 items-center gap-1">
            <LinkButton href={`/tasks/${task.id}/edit`} variant="ghost" className="h-9 w-9 px-0" title="Редагувати">
              <Pencil size={16} />
            </LinkButton>
            {(me.isAdmin || task.createdBy === me.id) && (
              <ActionButton action={deleteTaskAction.bind(null, task.id)} confirm="Видалити завдання? Особисті копії теж зникнуть." variant="danger" className="h-9 w-9 px-0" label="Видалити">
                <Trash2 size={16} />
              </ActionButton>
            )}
          </div>
        )}
      </div>

      <TaskWorkspace
        key={`${task.id}-${task.updatedAt.getTime()}`}
        taskId={task.id}
        kind={kind}
        base={task.content}
        work={work}
        fileName={fileName}
        allowRun={settings.allowPythonExecution}
      />
    </div>
  );
}
