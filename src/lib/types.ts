export type LessonKind = "lecture" | "seminar" | "practice" | "lab" | "video" | "reading" | "other";
export type TaskKind = "html" | "markdown" | "python";

export const LESSON_KIND_LABEL: Record<string, string> = {
  lecture: "Лекція",
  seminar: "Семінар",
  practice: "Практика",
  lab: "Лабораторна",
  video: "Відео",
  reading: "Читання",
  other: "Інше",
};

export const TASK_KIND_LABEL: Record<string, string> = {
  html: "HTML",
  markdown: "Markdown",
  python: "Python",
};

export const MATERIAL_KIND_LABEL: Record<string, string> = {
  link: "Посилання",
  document: "Файл",
  photo: "Фото",
  video: "Відео",
  audio: "Аудіо",
  voice: "Голосове",
};

export function formatDate(d: string | Date | null | undefined, long = false): string {
  if (!d) return "";
  const date = typeof d === "string" ? new Date(d + "T00:00:00") : d;
  return date.toLocaleDateString("uk-UA", long ? { day: "numeric", month: "long", year: "numeric" } : { day: "numeric", month: "short" });
}

export function youtubeId(url: string | null | undefined): string | null {
  if (!url) return null;
  const m = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/))([\w-]{11})/);
  return m ? m[1] : null;
}

export const SUBJECT_ICONS = [
  { key: "book", label: "Книга" },
  { key: "code", label: "Код" },
  { key: "database", label: "База даних" },
  { key: "cpu", label: "Процесор" },
  { key: "globe", label: "Веб" },
  { key: "calculator", label: "Математика" },
  { key: "terminal", label: "Термінал" },
  { key: "sparkles", label: "ШІ / ML" },
  { key: "graduation-cap", label: "Навчання" },
  { key: "flask", label: "Лабораторія" },
  { key: "languages", label: "Мови" },
  { key: "layers", label: "Шари" },
] as const;

export const SUBJECT_COLORS = [
  { key: "indigo", label: "Індиго", bg: "bg-indigo-500/10 dark:bg-indigo-500/20", text: "text-indigo-600 dark:text-indigo-400", border: "border-indigo-500/20", dot: "bg-indigo-500" },
  { key: "emerald", label: "Смарагдовий", bg: "bg-emerald-500/10 dark:bg-emerald-500/20", text: "text-emerald-600 dark:text-emerald-400", border: "border-emerald-500/20", dot: "bg-emerald-500" },
  { key: "sky", label: "Блакитний", bg: "bg-sky-500/10 dark:bg-sky-500/20", text: "text-sky-600 dark:text-sky-400", border: "border-sky-500/20", dot: "bg-sky-500" },
  { key: "amber", label: "Бурштиновий", bg: "bg-amber-500/10 dark:bg-amber-500/20", text: "text-amber-600 dark:text-amber-400", border: "border-amber-500/20", dot: "bg-amber-500" },
  { key: "rose", label: "Рожевий", bg: "bg-rose-500/10 dark:bg-rose-500/20", text: "text-rose-600 dark:text-rose-400", border: "border-rose-500/20", dot: "bg-rose-500" },
  { key: "violet", label: "Фіолетовий", bg: "bg-violet-500/10 dark:bg-violet-500/20", text: "text-violet-600 dark:text-violet-400", border: "border-violet-500/20", dot: "bg-violet-500" },
] as const;

export type SubjectColorKey = (typeof SUBJECT_COLORS)[number]["key"];
export type SubjectIconKey = (typeof SUBJECT_ICONS)[number]["key"];
