import { Archive, ArchiveRestore, ChevronLeft, ExternalLink, FileText, Pencil, Plus, Sparkles, Trash2, ClipboardList } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { deleteSubjectAction, setArchivedAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { MaterialsSection, TasksSection } from "@/components/Attachments";
import DoneToggle from "@/components/DoneToggle";
import { Badge, Card, Empty, LinkButton, Progress, SectionTitle } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getSubject, listLessons, listSubjectMaterials, listSubjectTasks } from "@/lib/data";
import { formatDate, LESSON_KIND_LABEL } from "@/lib/types";

export default async function SubjectPage({ params }: { params: Promise<{ id: string }> }) {
  const me = await requireUser();
  const { id: rawId } = await params;
  const id = Number(rawId);
  if (!Number.isInteger(id)) notFound();
  const subject = await getSubject(id);
  if (!subject) notFound();

  const [lessons, tasks, materials] = await Promise.all([listLessons(id, me.id), listSubjectTasks(id, me.id), listSubjectMaterials(id)]);
  const done = lessons.filter((l) => l.done).length;
  const isCourse = subject.kind === "course";
  const back = isCourse ? "/courses" : "/subjects";

  return (
    <div className="w-full">
      <Link href={back} className="mb-4 inline-flex items-center gap-1 text-sm text-muted transition hover:text-fg">
        <ChevronLeft size={15} /> {isCourse ? "Курси" : "Предмети"}
      </Link>

      <div className="mb-8">
        <div className="flex flex-wrap items-center gap-1.5">
          {subject.code && <Badge>{subject.code}</Badge>}
          {subject.year && (
            <Badge tone="indigo">
              {subject.year} курс · {subject.term ?? "?"} сем.
            </Badge>
          )}
          {subject.provider && <Badge>{subject.provider}</Badge>}
          {subject.isArchived && <Badge tone="amber">Архів</Badge>}
        </div>
        <div className="mt-3 flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{subject.title}</h1>
          </div>
          {me.canEdit && (
            <div className="flex shrink-0 items-center gap-1">
              <LinkButton href={`/subjects/${id}/edit`} variant="ghost" className="h-9 w-9 px-0" title="Редагувати">
                <Pencil size={16} />
              </LinkButton>
              <ActionButton action={setArchivedAction.bind(null, id, !subject.isArchived)} className="h-9 w-9 px-0" label={subject.isArchived ? "Повернути з архіву" : "В архів"}>
                {subject.isArchived ? <ArchiveRestore size={16} /> : <Archive size={16} />}
              </ActionButton>
              {(me.isAdmin || subject.createdBy === me.id) && (
                <ActionButton action={deleteSubjectAction.bind(null, id)} confirm="Видалити разом з усіма заняттями, матеріалами та завданнями?" variant="danger" className="h-9 w-9 px-0" label="Видалити">
                  <Trash2 size={16} />
                </ActionButton>
              )}
            </div>
          )}
        </div>
        {subject.description && <p className="mt-2 max-w-xl whitespace-pre-line text-sm leading-relaxed text-muted">{subject.description}</p>}
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
          {subject.instructor && <span>{subject.instructor}</span>}
          {subject.ects && <span>{subject.ects} ECTS</span>}
          {subject.url && (
            <a href={subject.url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-fg hover:underline">
              Сайт курсу <ExternalLink size={11} />
            </a>
          )}
        </div>
        <div className="mt-5 flex max-w-sm items-center gap-3">
          <Progress done={done} total={lessons.length} />
          <span className="text-xs tabular-nums text-muted">
            {done}/{lessons.length}
          </span>
        </div>
      </div>

      <SectionTitle
        action={
          me.canEdit && (
            <LinkButton href={`/lessons/new?subjectId=${id}`} variant="ghost" className="h-7 px-2 text-xs">
              <Plus size={13} /> Заняття
            </LinkButton>
          )
        }
      >
        Заняття
      </SectionTitle>
      <Card className="divide-y divide-line overflow-hidden">
        {lessons.map((l) => (
          <div key={l.id} className="flex items-center gap-3 px-4 py-3 transition hover:bg-surface-2/60">
            <DoneToggle lessonId={l.id} done={l.done} />
            <Link href={`/lessons/${l.id}`} className="flex min-w-0 flex-1 items-center gap-3">
              <div className="min-w-0 flex-1">
                <div className={`truncate text-sm font-medium ${l.done ? "text-faint line-through decoration-line-strong" : ""}`}>{l.title}</div>
                <div className="mt-0.5 text-xs text-faint">
                  {LESSON_KIND_LABEL[l.kind]} {l.number}
                  {l.heldOn ? ` · ${formatDate(l.heldOn)}` : ""}
                </div>
              </div>
              {l.taskCount > 0 && (
                <span title="Є завдання" className="flex items-center gap-1 text-xs text-faint">
                  <ClipboardList size={14} /> {l.taskCount}
                </span>
              )}
              {l.summary && (
                <span title="Є конспект" className="text-faint">
                  {l.summarySource === "ai" ? <Sparkles size={14} /> : <FileText size={14} />}
                </span>
              )}
            </Link>
          </div>
        ))}
        {lessons.length === 0 && <Empty>Занять поки немає</Empty>}
      </Card>

      <TasksSection tasks={tasks} canEdit={me.canEdit} subjectId={id} />
      <MaterialsSection materials={materials} me={me} subjectId={id} />
    </div>
  );
}
