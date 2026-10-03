import {
  integer,
  sqliteTable,
  text,
  index,
  primaryKey,
} from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";

/**
 * Схема SQLite для сайту Backnote.
 * Зберігає сумісність із полями бота та додає таблиці завдань і сесій.
 */

export const users = sqliteTable("users", {
  id: integer("id").primaryKey(), // Telegram ID (або числовий ID)
  username: text("username"),
  fullName: text("full_name"),
  status: text("status").notNull().default("pending"), // pending | active | blocked
  notifyNewContent: integer("notify_new_content", { mode: "boolean" }).notNull().default(true),
  createdAt: integer("created_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  lastSeenAt: integer("last_seen_at", { mode: "timestamp" }),
  // --- сайт ---
  login: text("login").unique(),
  passwordHash: text("password_hash"),
  isAdmin: integer("is_admin", { mode: "boolean" }).notNull().default(false),
  canEdit: integer("can_edit", { mode: "boolean" }).notNull().default(false),
});

export const webSessions = sqliteTable(
  "web_sessions",
  {
    id: text("id").primaryKey(), // sha256 від токена з cookie
    userId: integer("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    expiresAt: integer("expires_at", { mode: "timestamp" }).notNull(),
    createdAt: integer("created_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  },
  (t) => [index("ix_web_sessions_user").on(t.userId)],
);

export const subjects = sqliteTable("subjects", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  kind: text("kind").notNull().default("subject"), // subject | course
  title: text("title").notNull(),
  code: text("code"),
  instructor: text("instructor"),
  description: text("description"),
  year: integer("year"),
  term: integer("term"),
  ects: integer("ects"),
  provider: text("provider"),
  url: text("url"),
  isArchived: integer("is_archived", { mode: "boolean" }).notNull().default(false),
  icon: text("icon"), // lucide icon identifier
  color: text("color"), // indigo | emerald | sky | amber | rose | violet
  createdBy: integer("created_by").references(() => users.id, { onDelete: "set null" }),
  createdAt: integer("created_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  updatedAt: integer("updated_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
});

export const lessons = sqliteTable(
  "lessons",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    subjectId: integer("subject_id")
      .notNull()
      .references(() => subjects.id, { onDelete: "cascade" }),
    number: integer("number").notNull(),
    kind: text("kind").notNull().default("lecture"),
    title: text("title").notNull(),
    description: text("description"),
    videoUrl: text("video_url"),
    heldOn: text("held_on"), // YYYY-MM-DD
    summary: text("summary"),
    summarySource: text("summary_source"), // manual | ai
    summaryUpdatedAt: integer("summary_updated_at", { mode: "timestamp" }),
    summaryBy: integer("summary_by").references(() => users.id, { onDelete: "set null" }),
    createdBy: integer("created_by").references(() => users.id, { onDelete: "set null" }),
    createdAt: integer("created_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
    updatedAt: integer("updated_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  },
  (t) => [index("ix_lessons_subject_id").on(t.subjectId)],
);

export const materials = sqliteTable(
  "materials",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    subjectId: integer("subject_id")
      .notNull()
      .references(() => subjects.id, { onDelete: "cascade" }),
    lessonId: integer("lesson_id").references(() => lessons.id, { onDelete: "cascade" }),
    kind: text("kind").notNull(), // link | document | photo | video | audio | voice
    title: text("title").notNull(),
    url: text("url"),
    fileId: text("file_id"), // Telegram file_id (файли доступні лише в боті)
    createdBy: integer("created_by").references(() => users.id, { onDelete: "set null" }),
    createdAt: integer("created_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  },
  (t) => [index("ix_materials_subject_id").on(t.subjectId), index("ix_materials_lesson_id").on(t.lessonId)],
);

export const lessonProgress = sqliteTable(
  "lesson_progress",
  {
    userId: integer("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    lessonId: integer("lesson_id")
      .notNull()
      .references(() => lessons.id, { onDelete: "cascade" }),
    completedAt: integer("completed_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  },
  (t) => [primaryKey({ columns: [t.userId, t.lessonId] })],
);

export const lessonNotes = sqliteTable(
  "lesson_notes",
  {
    userId: integer("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    lessonId: integer("lesson_id")
      .notNull()
      .references(() => lessons.id, { onDelete: "cascade" }),
    text: text("text").notNull(),
    updatedAt: integer("updated_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  },
  (t) => [primaryKey({ columns: [t.userId, t.lessonId] })],
);

/** Завдання: HTML-сторінка (тест/вправи), Markdown або Python-файл. Прикріплюється до предмета і (за бажанням) до заняття. */
export const tasks = sqliteTable(
  "tasks",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    subjectId: integer("subject_id")
      .notNull()
      .references(() => subjects.id, { onDelete: "cascade" }),
    lessonId: integer("lesson_id").references(() => lessons.id, { onDelete: "cascade" }),
    title: text("title").notNull(),
    kind: text("kind").notNull(), // html | markdown | python
    content: text("content").notNull(),
    fileName: text("file_name"),
    createdBy: integer("created_by").references(() => users.id, { onDelete: "set null" }),
    createdAt: integer("created_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
    updatedAt: integer("updated_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  },
  (t) => [index("ix_tasks_subject_id").on(t.subjectId), index("ix_tasks_lesson_id").on(t.lessonId)],
);

/** Особиста копія завдання користувача. Немає рядка — користувач працює з базовою версією. */
export const taskWork = sqliteTable(
  "task_work",
  {
    userId: integer("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    taskId: integer("task_id")
      .notNull()
      .references(() => tasks.id, { onDelete: "cascade" }),
    content: text("content").notNull(),
    updatedAt: integer("updated_at", { mode: "timestamp" }).notNull().default(sql`(unixepoch())`),
  },
  (t) => [primaryKey({ columns: [t.userId, t.taskId] })],
);
