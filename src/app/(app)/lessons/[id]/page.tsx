import { ArrowLeft, ArrowRight, ChevronLeft, ExternalLink, Pencil, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { deleteLessonAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { MaterialsSection, TasksSection } from "@/components/Attachments";
import DoneToggle from "@/components/DoneToggle";
import { NoteEditor, VideoEmbed } from "@/components/LessonClient";
import { Markdown } from "@/components/Markdown";
import { Badge, Card, LinkButton, SectionTitle } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getLessonBundle } from "@/lib/data";
import { formatDate, LESSON_KIND_LABEL, youtubeId } from "@/lib/types";

export default async function LessonPage({ params }: { params: Promise<{ id: string }> }) {
  const me = await requireUser();
  const { id: raw } = await params;
  const id = Number(raw);
  if (!Number.isInteger(id)) notFound();
  const b = await getLessonBundle(id, me.id);
  if (!b) notFound();
  const { lesson, subject } = b;
  const yt = youtubeId(lesson.videoUrl);

  return (
    <div className="w-full">
      <Link href={`/subjects/${subject.id}`} className="mb-4 inline-flex items-center gap-1 text-sm text-muted transition hover:text-fg">
        <ChevronLeft size={15} /> {subject.title}
      </Link>

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Badge>
            {LESSON_KIND_LABEL[lesson.kind]} {lesson.number}
          </Badge>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight">{lesson.title}</h1>
          {lesson.heldOn && <p className="mt-1 text-xs text-faint">{formatDate(lesson.heldOn, true)}</p>}
        </div>
        <DoneToggle lessonId={lesson.id} done={b.done} variant="button" />
      </div>

      {me.canEdit && (
        <div className="mt-3 flex items-center gap-1.5">
          <LinkButton href={`/lessons/${lesson.id}/edit`} variant="ghost" className="h-8 px-2.5 text-xs font-medium">
            <Pencil size={15} /> Редагувати
          </LinkButton>
          {(me.isAdmin || lesson.createdBy === me.id) && (
            <ActionButton action={deleteLessonAction.bind(null, lesson.id)} confirm="Видалити заняття разом із завданнями та матеріалами?" variant="danger" className="h-8 px-2.5 text-xs font-medium">
              <Trash2 size={15} /> Видалити
            </ActionButton>
          )}
        </div>
      )}

      {lesson.description && <p className="mt-4 whitespace-pre-line text-sm leading-relaxed text-muted">{lesson.description}</p>}

      {yt ? (
        <VideoEmbed id={yt} />
      ) : (
        lesson.videoUrl && (
          <a href={lesson.videoUrl} target="_blank" rel="noreferrer noopener" className="group mt-5 block">
            <Card className="flex items-center gap-3 p-3 transition group-hover:border-line-strong">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-fg">
                <ExternalLink size={15} />
              </div>
              <div className="text-sm">
                <div className="font-medium">Запис заняття</div>
                <div className="text-xs text-faint">Відкрити відео</div>
              </div>
            </Card>
          </a>
        )
      )}

      <TasksSection tasks={b.tasks} canEdit={me.canEdit} subjectId={subject.id} lessonId={lesson.id} />

      <section className="mt-8">
        <SectionTitle
          action={
            lesson.summary && (
              <Badge tone={lesson.summarySource === "ai" ? "indigo" : "zinc"}>
                {lesson.summarySource === "ai" && <Sparkles size={10} />} {lesson.summarySource === "ai" ? "Gemini" : "Вручну"}
              </Badge>
            )
          }
        >
          Конспект
        </SectionTitle>
        <Card className="p-5">
          {lesson.summary ? (
            <Markdown source={lesson.summary} />
          ) : (
            <p className="text-sm text-faint">Конспекту ще немає. {me.canEdit ? "Додай його через «Редагувати» або в боті." : "Його можна додати в боті."}</p>
          )}
        </Card>
      </section>

      <MaterialsSection materials={b.materials} me={me} subjectId={subject.id} lessonId={lesson.id} />
      <NoteEditor lessonId={lesson.id} initial={b.note} />

      <div className="mt-8 flex justify-between gap-3">
        {b.prevId ? (
          <LinkButton href={`/lessons/${b.prevId}`}>
            <ArrowLeft size={14} /> Назад
          </LinkButton>
        ) : (
          <span />
        )}
        {b.nextId && (
          <LinkButton href={`/lessons/${b.nextId}`}>
            Далі <ArrowRight size={14} />
          </LinkButton>
        )}
      </div>
    </div>
  );
}
