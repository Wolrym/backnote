"use client";

import {
  Archive,
  Book,
  Code,
  Database,
  Cpu,
  Globe,
  Calculator,
  Terminal,
  Sparkles,
  GraduationCap,
  FlaskConical,
  Languages,
  Layers,
} from "lucide-react";
import Link from "next/link";
import { useState, useMemo } from "react";
import { Badge, Card, Empty, Progress } from "@/components/ui";
import { SUBJECT_COLORS, type SubjectColorKey } from "@/lib/types";

const ICON_MAP = {
  book: Book,
  code: Code,
  database: Database,
  cpu: Cpu,
  globe: Globe,
  calculator: Calculator,
  terminal: Terminal,
  sparkles: Sparkles,
  "graduation-cap": GraduationCap,
  flask: FlaskConical,
  languages: Languages,
  layers: Layers,
} as const;

export type SubjectItem = {
  id: number;
  kind: string;
  title: string;
  code: string | null;
  instructor: string | null;
  year: number | null;
  term: number | null;
  provider: string | null;
  isArchived: boolean;
  icon: string | null;
  color: string | null;
  done: number;
  total: number;
};

export default function CatalogView({
  items,
  kind,
  showArchived,
  archivedCount,
}: {
  items: SubjectItem[];
  kind: "subject" | "course";
  showArchived: boolean;
  archivedCount: number;
}) {
  const [selectedYear, setSelectedYear] = useState<number | "all">("all");
  const base = kind === "subject" ? "/subjects" : "/courses";

  // Знаходимо всі наявні курси (роки навчання)
  const availableYears = useMemo(() => {
    if (kind !== "subject") return [];
    const years = new Set<number>();
    items.forEach((s) => {
      if (s.year) years.add(s.year);
    });
    return Array.from(years).sort((a, b) => a - b);
  }, [items, kind]);

  // Фільтруємо предмети за обраним роком
  const filteredItems = useMemo(() => {
    if (selectedYear === "all" || kind !== "subject") return items;
    return items.filter((s) => s.year === selectedYear);
  }, [items, selectedYear, kind]);

  const getColorClasses = (colorKey: string | null | undefined) => {
    const found = SUBJECT_COLORS.find((c) => c.key === colorKey) || SUBJECT_COLORS[0];
    return found;
  };

  return (
    <div className="space-y-6">
      {/* Фільтр за курсами, якщо є предмети з різними роками навчання */}
      {availableYears.length > 1 && (
        <div className="flex flex-wrap items-center gap-1.5 border-b border-line/60 pb-3">
          <button
            onClick={() => setSelectedYear("all")}
            className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              selectedYear === "all"
                ? "bg-surface-2 text-fg shadow-sm border border-line"
                : "text-muted hover:text-fg hover:bg-surface-2/50"
            }`}
          >
            Усі предмети ({items.length})
          </button>
          {availableYears.map((year) => {
            const count = items.filter((s) => s.year === year).length;
            return (
              <button
                key={year}
                onClick={() => setSelectedYear(year)}
                className={`cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  selectedYear === year
                    ? "bg-surface-2 text-fg shadow-sm border border-line"
                    : "text-muted hover:text-fg hover:bg-surface-2/50"
                }`}
              >
                {year} курс ({count})
              </button>
            );
          })}
        </div>
      )}

      {/* Головна сітка блоків: тепер картки стоять поруч одна біля одної */}
      {filteredItems.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredItems.map((s) => {
            const IconComp =
              (s.icon && ICON_MAP[s.icon as keyof typeof ICON_MAP]) ||
              (kind === "course" ? Sparkles : Book);
            const color = getColorClasses(s.color);

            return (
              <Link key={s.id} href={`/subjects/${s.id}`} className="group flex">
                <Card className="flex w-full flex-col justify-between p-4.5 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:border-line-strong group-hover:shadow-md">
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div
                        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${color.bg} ${color.text} ${color.border}`}
                      >
                        <IconComp size={18} />
                      </div>

                      <div className="flex flex-wrap justify-end gap-1.5">
                        {s.code && <Badge>{s.code}</Badge>}
                        {s.provider && <Badge>{s.provider}</Badge>}
                        {s.year && (
                          <Badge tone="indigo">
                            {s.year} курс{s.term ? ` · ${s.term} сем` : ""}
                          </Badge>
                        )}
                        {s.isArchived && <Badge tone="amber">Архів</Badge>}
                      </div>
                    </div>

                    <div className="mt-3.5 text-sm font-semibold leading-snug transition group-hover:text-accent-fg-hover">
                      {s.title}
                    </div>

                    {s.instructor && (
                      <div className="mt-1 text-xs text-muted truncate">{s.instructor}</div>
                    )}
                  </div>

                  <div className="mt-5 border-t border-line/50 pt-3">
                    <div className="mb-1.5 flex items-center justify-between text-xs text-muted">
                      <span>Прогрес</span>
                      <span className="tabular-nums font-medium">
                        {s.done}/{s.total}{" "}
                        {s.total > 0 && `(${Math.round((s.done / s.total) * 100)}%)`}
                      </span>
                    </div>
                    <Progress done={s.done} total={s.total} />
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      ) : (
        <Card>
          <Empty>{showArchived ? "В архіві порожньо" : "Тут поки нічого немає"}</Empty>
        </Card>
      )}

      {(archivedCount > 0 || showArchived) && (
        <div className="pt-2">
          <Link
            href={showArchived ? base : `${base}?archived=1`}
            className="inline-flex items-center gap-1.5 text-xs text-muted transition hover:text-fg"
          >
            <Archive size={14} /> {showArchived ? "Назад до активних" : `Архів (${archivedCount})`}
          </Link>
        </div>
      )}
    </div>
  );
}
