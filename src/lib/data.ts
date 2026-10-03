import { and, asc, desc, eq, like, isNull, or, sql } from "drizzle-orm";
import { db } from "@/db";
import {
  lessonNotes,
  lessonProgress,
  lessons,
  materials,
  subjects,
  taskWork,
  tasks,
  users,
} from "@/db/schema";

export type Subject = typeof subjects.$inferSelect;
export type Lesson = typeof lessons.$inferSelect;
export type Task = typeof tasks.$inferSelect;

export async function listSubjects(userId: number, kind?: "subject" | "course") {
  const rows = await db
    .select({
      subject: subjects,
      total: sql<number>`cast(count(distinct ${lessons.id}) as integer)`,
      done: sql<number>`cast(count(distinct ${lessonProgress.lessonId}) as integer)`,
    })
    .from(subjects)
    .leftJoin(lessons, eq(lessons.subjectId, subjects.id))
    .leftJoin(lessonProgress, and(eq(lessonProgress.lessonId, lessons.id), eq(lessonProgress.userId, userId)))
    .where(kind ? eq(subjects.kind, kind) : undefined)
    .groupBy(subjects.id)
    // найновіший семестр першим, як у боті
    .orderBy(desc(subjects.year), desc(subjects.term), asc(subjects.title));
  return rows.map((r) => ({ ...r.subject, total: r.total, done: r.done }));
}

export async function getSubject(id: number) {
  if (!Number.isInteger(id)) return null;
  const [row] = await db.select().from(subjects).where(eq(subjects.id, id)).limit(1);
  return row ?? null;
}

export async function listLessons(subjectId: number, userId: number) {
  const rows = await db
    .select({
      lesson: lessons,
      done: sql<boolean>`${lessonProgress.lessonId} is not null`,
      taskCount: sql<number>`cast((select count(*) from tasks t where t.lesson_id = ${lessons.id}) as integer)`,
    })
    .from(lessons)
    .leftJoin(lessonProgress, and(eq(lessonProgress.lessonId, lessons.id), eq(lessonProgress.userId, userId)))
    .where(eq(lessons.subjectId, subjectId))
    .orderBy(asc(lessons.number), asc(lessons.id));
  return rows.map((r) => ({ ...r.lesson, done: r.done, taskCount: r.taskCount }));
}

export async function getLessonBundle(lessonId: number, userId: number) {
  const [lesson] = await db.select().from(lessons).where(eq(lessons.id, lessonId)).limit(1);
  if (!lesson) return null;
  const subject = await getSubject(lesson.subjectId);
  if (!subject) return null;

  const [siblings, mats, lessonTasks, [progress], [note]] = await Promise.all([
    db
      .select({ id: lessons.id })
      .from(lessons)
      .where(eq(lessons.subjectId, lesson.subjectId))
      .orderBy(asc(lessons.number), asc(lessons.id)),
    db.select().from(materials).where(eq(materials.lessonId, lessonId)).orderBy(asc(materials.createdAt), asc(materials.id)),
    db
      .select({
        id: tasks.id,
        title: tasks.title,
        kind: tasks.kind,
        modified: sql<boolean>`${taskWork.taskId} is not null`,
      })
      .from(tasks)
      .leftJoin(taskWork, and(eq(taskWork.taskId, tasks.id), eq(taskWork.userId, userId)))
      .where(eq(tasks.lessonId, lessonId))
      .orderBy(asc(tasks.id)),
    db
      .select()
      .from(lessonProgress)
      .where(and(eq(lessonProgress.lessonId, lessonId), eq(lessonProgress.userId, userId)))
      .limit(1),
    db
      .select()
      .from(lessonNotes)
      .where(and(eq(lessonNotes.lessonId, lessonId), eq(lessonNotes.userId, userId)))
      .limit(1),
  ]);

  const idx = siblings.findIndex((s) => s.id === lessonId);
  return {
    lesson,
    subject,
    materials: mats,
    tasks: lessonTasks,
    done: !!progress,
    note: note?.text ?? "",
    prevId: idx > 0 ? siblings[idx - 1].id : null,
    nextId: idx >= 0 && idx + 1 < siblings.length ? siblings[idx + 1].id : null,
  };
}

/** Завдання предмета, не прив'язані до конкретного заняття. */
export async function listSubjectTasks(subjectId: number, userId: number) {
  return db
    .select({
      id: tasks.id,
      title: tasks.title,
      kind: tasks.kind,
      modified: sql<boolean>`${taskWork.taskId} is not null`,
    })
    .from(tasks)
    .leftJoin(taskWork, and(eq(taskWork.taskId, tasks.id), eq(taskWork.userId, userId)))
    .where(and(eq(tasks.subjectId, subjectId), isNull(tasks.lessonId)))
    .orderBy(asc(tasks.id));
}

export async function listSubjectMaterials(subjectId: number) {
  return db
    .select()
    .from(materials)
    .where(and(eq(materials.subjectId, subjectId), isNull(materials.lessonId)))
    .orderBy(asc(materials.createdAt), asc(materials.id));
}

export async function getTaskBundle(taskId: number, userId: number) {
  const [task] = await db.select().from(tasks).where(eq(tasks.id, taskId)).limit(1);
  if (!task) return null;
  const [subject, lessonRows, workRows] = await Promise.all([
    getSubject(task.subjectId),
    task.lessonId ? db.select().from(lessons).where(eq(lessons.id, task.lessonId)).limit(1) : Promise.resolve([]),
    db
      .select()
      .from(taskWork)
      .where(and(eq(taskWork.taskId, taskId), eq(taskWork.userId, userId)))
      .limit(1),
  ]);
  if (!subject) return null;
  return { task, subject, lesson: lessonRows[0] ?? null, work: workRows[0]?.content ?? null };
}

export async function getHome(userId: number) {
  const list = (await listSubjects(userId)).filter((s) => !s.isArchived);
  const total = list.reduce((a, s) => a + s.total, 0);
  const done = list.reduce((a, s) => a + s.done, 0);

  // «Продовжити»: перше непройдене заняття в першому активному предметі, де воно є.
  let next: { lessonId: number; title: string; kind: string; number: number; subject: string } | null = null;
  for (const s of list) {
    if (s.done >= s.total) continue;
    const [l] = await db
      .select({ id: lessons.id, title: lessons.title, kind: lessons.kind, number: lessons.number })
      .from(lessons)
      .leftJoin(lessonProgress, and(eq(lessonProgress.lessonId, lessons.id), eq(lessonProgress.userId, userId)))
      .where(and(eq(lessons.subjectId, s.id), isNull(lessonProgress.lessonId)))
      .orderBy(asc(lessons.number), asc(lessons.id))
      .limit(1);
    if (l) {
      next = { lessonId: l.id, title: l.title, kind: l.kind, number: l.number, subject: s.title };
      break;
    }
  }
  return { subjects: list, total, done, next };
}

export async function search(q: string) {
  const pattern = `%${q.replace(/[\\%_]/g, "\\$&")}%`;
  const [subjectRows, lessonRows, taskRows] = await Promise.all([
    db
      .select()
      .from(subjects)
      .where(or(like(subjects.title, pattern), like(subjects.code, pattern), like(subjects.description, pattern)))
      .limit(20),
    db
      .select({ lesson: lessons, subjectTitle: subjects.title })
      .from(lessons)
      .innerJoin(subjects, eq(subjects.id, lessons.subjectId))
      .where(or(like(lessons.title, pattern), like(lessons.description, pattern), like(lessons.summary, pattern)))
      .orderBy(sql`case when ${lessons.title} like ${pattern} then 0 else 1 end`)
      .limit(30),
    db
      .select({ id: tasks.id, title: tasks.title, kind: tasks.kind, subjectTitle: subjects.title })
      .from(tasks)
      .innerJoin(subjects, eq(subjects.id, tasks.subjectId))
      .where(like(tasks.title, pattern))
      .limit(20),
  ]);
  return { subjects: subjectRows, lessons: lessonRows, tasks: taskRows };
}

export async function listUsers() {
  return db.select().from(users).orderBy(asc(users.createdAt));
}
