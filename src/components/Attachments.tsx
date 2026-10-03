"use client";

import { ChevronDown, ClipboardList, ExternalLink, File, FileCode2, FileText, Globe, Link2, Play, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { addMaterialAction, deleteMaterialAction } from "@/app/actions";
import ActionButton from "@/components/ActionButton";
import { VideoEmbed } from "@/components/LessonClient";
import { Badge, Button, Card, inputClass, LinkButton, SectionTitle } from "@/components/ui";
import type { SessionUser } from "@/lib/auth";
import { MATERIAL_KIND_LABEL, TASK_KIND_LABEL, youtubeId } from "@/lib/types";

type TaskRow = { id: number; title: string; kind: string; modified: boolean };
type MaterialRow = { id: number; kind: string; title: string; url: string | null; createdBy: number | null };

export const TaskIcon = ({ kind, size = 16 }: { kind: string; size?: number }) =>
  kind === "python" ? <FileCode2 size={size} /> : kind === "html" ? <Globe size={size} /> : <FileText size={size} />;

export function TasksSection({
  tasks,
  canEdit,
  subjectId,
  lessonId,
}: {
  tasks: TaskRow[];
  canEdit: boolean;
  subjectId: number;
  lessonId?: number;
}) {
  if (!tasks.length && !canEdit) return null;
  const q = new URLSearchParams({ subjectId: String(subjectId), ...(lessonId ? { lessonId: String(lessonId) } : {}) });
  return (
    <section className="mt-8">
      <SectionTitle
        action={
          canEdit && (
            <LinkButton href={`/tasks/new?${q}`} variant="ghost" className="h-8 px-2.5 text-xs font-medium">
              <Plus size={15} /> Завдання
            </LinkButton>
          )
        }
      >
        Завдання
      </SectionTitle>
      <Card className="divide-y divide-line overflow-hidden">
        {tasks.map((t) => (
          <Link key={t.id} href={`/tasks/${t.id}`} className="flex items-center gap-3 px-4 py-3 transition hover:bg-surface-2/60">
            <span className="text-faint">
              <TaskIcon kind={t.kind} />
            </span>
            <span className="min-w-0 flex-1 truncate text-sm font-medium">{t.title}</span>
            {t.modified && <Badge tone="indigo">Моя копія</Badge>}
            <Badge>{TASK_KIND_LABEL[t.kind]}</Badge>
          </Link>
        ))}
        {!tasks.length && (
          <div className="flex items-center gap-2 px-4 py-6 text-sm text-faint">
            <ClipboardList size={15} /> Завдань ще немає
          </div>
        )}
      </Card>
    </section>
  );
}

export function MaterialsSection({
  materials,
  me,
  subjectId,
  lessonId,
}: {
  materials: MaterialRow[];
  me: SessionUser;
  subjectId: number;
  lessonId?: number;
}) {
  const [openYt, setOpenYt] = useState<number | null>(null);

  if (!materials.length && !me.canEdit) return null;
  return (
    <section className="mt-8">
      <SectionTitle>Матеріали</SectionTitle>
      <Card className="divide-y divide-line overflow-hidden">
        {materials.map((m) => {
          const ytId = youtubeId(m.url);
          const isYtOpen = openYt === m.id;

          const body = (
            <>
              <span className="text-faint">{ytId ? <Play size={15} className="text-red-500" /> : m.url ? <Link2 size={15} /> : <File size={15} />}</span>
              <span className="min-w-0 flex-1 truncate text-sm">{m.title}</span>
              {ytId ? (
                <Badge tone="indigo">YouTube · плеєр</Badge>
              ) : m.url ? (
                <ExternalLink size={13} className="text-faint" />
              ) : (
                <Badge>{MATERIAL_KIND_LABEL[m.kind]} · у боті</Badge>
              )}
            </>
          );

          return (
            <div key={m.id} className="transition hover:bg-surface-2/60">
              <div className="flex items-center gap-1 pr-2">
                {ytId ? (
                  <button
                    type="button"
                    onClick={() => setOpenYt(isYtOpen ? null : m.id)}
                    className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 px-4 py-3 text-left"
                  >
                    {body}
                    <ChevronDown size={14} className={`text-faint transition-transform ${isYtOpen ? "rotate-180" : ""}`} />
                  </button>
                ) : m.url ? (
                  <a href={m.url} target="_blank" rel="noreferrer noopener" className="flex min-w-0 flex-1 items-center gap-3 px-4 py-3">
                    {body}
                  </a>
                ) : (
                  <div className="flex min-w-0 flex-1 items-center gap-3 px-4 py-3">{body}</div>
                )}

                {me.canEdit && (me.isAdmin || m.createdBy === me.id) && (
                  <ActionButton action={deleteMaterialAction.bind(null, m.id)} confirm="Видалити матеріал?" variant="danger" className="h-8 w-8 px-0" label="Видалити">
                    <Trash2 size={15} />
                  </ActionButton>
                )}
              </div>

              {/* Вбудований відеоплеєр прямо на сторінці */}
              {ytId && isYtOpen && (
                <div className="px-4 pb-4 pt-1">
                  <VideoEmbed id={ytId} />
                </div>
              )}
            </div>
          );
        })}
        {!materials.length && <div className="px-4 py-6 text-sm text-faint">Матеріалів ще немає</div>}
        {me.canEdit && (
          <details className="group">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-2.5 text-xs text-muted transition hover:text-fg [&::-webkit-details-marker]:hidden">
              <Plus size={15} /> Додати посилання або YouTube-відео
            </summary>
            <form action={addMaterialAction} className="flex flex-col gap-2 px-4 pb-4 sm:flex-row">
              <input type="hidden" name="subjectId" value={subjectId} />
              {lessonId && <input type="hidden" name="lessonId" value={lessonId} />}
              <input name="url" required placeholder="https://youtube.com/watch?v=... або https://…" className={inputClass} />
              <input name="title" placeholder="Назва матеріалу" className={inputClass} />
              <Button variant="primary">Додати</Button>
            </form>
          </details>
        )}
      </Card>
      <p className="mt-2 text-xs text-faint">YouTube-посилання можна переглядати безпосередньо на сайті або відкривати окремо. Файли (PDF, слайди) доступні в Telegram-боті.</p>
    </section>
  );
}
