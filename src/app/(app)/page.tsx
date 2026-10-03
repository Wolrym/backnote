import { ArrowRight, CheckCircle2, Flame, Layers } from "lucide-react";
import Link from "next/link";
import { Badge, Card, Empty, PageHeader, Progress, SectionTitle } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getHome } from "@/lib/data";
import { LESSON_KIND_LABEL } from "@/lib/types";

export default async function HomePage() {
  const me = await requireUser();
  const { subjects, total, done, next } = await getHome(me.id);

  const stats = [
    { icon: CheckCircle2, label: "Пройдено", value: `${done}/${total}` },
    { icon: Layers, label: "Активних предметів і курсів", value: String(subjects.length) },
    { icon: Flame, label: "Загальний прогрес", value: `${total ? Math.round((done / total) * 100) : 0}%` },
  ];

  return (
    <div className="w-full space-y-8">
      <PageHeader title={`Привіт, ${me.fullName.split(" ")[0]} 👋`} subtitle="Ось твій прогрес навчання" />

      <div className="grid gap-3 sm:grid-cols-3">
        {stats.map((s) => (
          <Card key={s.label} className="p-4">
            <s.icon size={16} className="text-faint" />
            <div className="mt-3 text-2xl font-semibold tracking-tight">{s.value}</div>
            <div className="text-xs text-muted">{s.label}</div>
          </Card>
        ))}
      </div>

      {next && (
        <Link href={`/lessons/${next.lessonId}`} className="group block">
          <Card className="flex items-center justify-between gap-4 p-5 transition group-hover:border-line-strong group-hover:shadow-md">
            <div className="min-w-0">
              <div className="text-xs font-medium uppercase tracking-wider text-faint">Продовжити</div>
              <div className="mt-1 truncate text-base font-medium">{next.title}</div>
              <div className="mt-1.5 flex items-center gap-2 text-xs text-muted">
                <Badge>
                  {LESSON_KIND_LABEL[next.kind]} {next.number}
                </Badge>
                <span className="truncate">{next.subject}</span>
              </div>
            </div>
            <ArrowRight size={18} className="shrink-0 text-faint transition group-hover:translate-x-1 group-hover:text-fg" />
          </Card>
        </Link>
      )}

      <div>
        <SectionTitle>Прогрес за предметами</SectionTitle>
        <Card className="divide-y divide-line overflow-hidden">
          {subjects.map((s) => (
            <Link key={s.id} href={`/subjects/${s.id}`} className="flex items-center gap-4 px-4 py-3 transition hover:bg-surface-2/60">
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{s.title}</div>
                <Progress done={s.done} total={s.total} className="mt-2" />
              </div>
              <span className="w-10 text-right text-xs tabular-nums text-muted">
                {s.done}/{s.total}
              </span>
            </Link>
          ))}
          {subjects.length === 0 && <Empty>Поки немає предметів. {me.canEdit ? "Додай перший у розділі «Предмети»." : ""}</Empty>}
        </Card>
      </div>
    </div>
  );
}
