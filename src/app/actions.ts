"use server";

import { and, eq, max, sql } from "drizzle-orm";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
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
  webSessions,
} from "@/db/schema";
import {
  createSession,
  destroySession,
  generatePassword,
  hashPassword,
  requireAdmin,
  requireEditor,
  requireUser,
  verifyPassword,
  type SessionUser,
} from "@/lib/auth";
import { DEMO_LESSONS, DEMO_SUBJECTS, DEMO_TASKS } from "@/lib/demo";
import { updateAppSettings } from "@/lib/settings";

export type FormState = { error?: string; ok?: string; password?: string } | undefined;

const MAX_CONTENT = 15_000_000;
const refresh = () => revalidatePath("/", "layout");

const str = (f: FormData, k: string, max = 1024): string | null => {
  const v = String(f.get(k) ?? "").trim();
  return v ? v.slice(0, max) : null;
};
const int = (f: FormData, k: string): number | null => {
  const v = String(f.get(k) ?? "").trim();
  if (!v) return null;
  const n = Number(v);
  return Number.isInteger(n) ? n : null;
};
const safeUrl = (v: string | null): string | null => {
  if (!v) return null;
  const withProto = /^https?:\/\//i.test(v) ? v : `https://${v}`;
  try {
    return new URL(withProto).toString();
  } catch {
    return null;
  }
};
const canDelete = (u: SessionUser, createdBy: number | null) => u.isAdmin || createdBy === u.id;

/* ───────────────────────── Авторизація ───────────────────────── */

const attempts = new Map<string, { n: number; until: number }>();

export async function loginAction(_: FormState, f: FormData): Promise<FormState> {
  const login = String(f.get("login") ?? "").trim().toLowerCase();
  const password = String(f.get("password") ?? "");
  if (!login || !password) return { error: "Введи логін і пароль" };

  const a = attempts.get(login);
  if (a && a.n >= 8 && a.until > Date.now()) return { error: "Забагато спроб. Спробуй за кілька хвилин." };

  const [user] = await db.select().from(users).where(eq(users.login, login)).limit(1);
  const ok = verifyPassword(password, user?.passwordHash ?? null);
  if (!user || !ok) {
    attempts.set(login, { n: (a && a.until > Date.now() ? a.n : 0) + 1, until: Date.now() + 10 * 60_000 });
    return { error: "Невірний логін або пароль" };
  }
  if (user.status === "blocked") return { error: "Доступ заблоковано" };
  if (user.status !== "active") return { error: "Акаунт ще не активовано адміном" };

  attempts.delete(login);
  await createSession(user.id);
  await db.update(users).set({ lastSeenAt: new Date() }).where(eq(users.id, user.id));
  redirect("/");
}

export async function logoutAction() {
  await destroySession();
  redirect("/login");
}

/** Перший запуск: створення адміна (працює лише поки адміна ще немає). */
export async function setupAction(_: FormState, f: FormData): Promise<FormState> {
  const [{ n }] = await db.select({ n: sql<number>`cast(count(*) as integer)` }).from(users).where(eq(users.isAdmin, true));
  if (n > 0) return { error: "Адмін уже створений" };

  const tgId = int(f, "telegramId");
  const login = (str(f, "login", 64) ?? "").toLowerCase();
  const password = String(f.get("password") ?? "");
  const fullName = str(f, "fullName", 256);
  if (!tgId || tgId <= 0) return { error: "Вкажи Telegram ID (той самий, що ADMIN_ID у боті)" };
  if (!/^[a-z0-9_.-]{3,64}$/.test(login)) return { error: "Логін: 3–64 символи, латиниця, цифри, _ . -" };
  if (password.length < 8) return { error: "Пароль має бути не коротший за 8 символів" };

  const values = {
    id: tgId,
    fullName: fullName ?? login,
    login,
    passwordHash: hashPassword(password),
    status: "active",
    isAdmin: true,
    canEdit: true,
  };
  await db
    .insert(users)
    .values(values)
    .onConflictDoUpdate({ target: users.id, set: { ...values } });

  if (f.get("demo") === "on") await seedDemo(tgId);
  await createSession(tgId);
  redirect("/");
}

async function seedDemo(authorId: number) {
  const subjectIds = new Map<string, number>();
  for (const s of DEMO_SUBJECTS) {
    const [row] = await db.insert(subjects).values({ ...s, createdBy: authorId }).returning({ id: subjects.id });
    subjectIds.set(s.key, row.id);
  }
  const lessonIds = new Map<string, number>();
  for (const l of DEMO_LESSONS) {
    const { key, subject, ...rest } = l;
    const [row] = await db
      .insert(lessons)
      .values({ ...rest, subjectId: subjectIds.get(subject)!, createdBy: authorId, summaryUpdatedAt: "summary" in l ? new Date() : null })
      .returning({ id: lessons.id, subjectId: lessons.subjectId });
    lessonIds.set(key, row.id);
  }
  for (const t of DEMO_TASKS) {
    const lessonId = lessonIds.get(t.lesson)!;
    const [lesson] = await db.select({ subjectId: lessons.subjectId }).from(lessons).where(eq(lessons.id, lessonId));
    await db.insert(tasks).values({
      subjectId: lesson.subjectId,
      lessonId,
      title: t.title,
      kind: t.kind,
      content: t.content,
      fileName: t.fileName,
      createdBy: authorId,
    });
  }
}

export async function changePasswordAction(_: FormState, f: FormData): Promise<FormState> {
  const me = await requireUser();
  const current = String(f.get("current") ?? "");
  const next = String(f.get("next") ?? "");
  const [row] = await db.select().from(users).where(eq(users.id, me.id));
  if (!verifyPassword(current, row?.passwordHash ?? null)) return { error: "Поточний пароль невірний" };
  if (next.length < 8) return { error: "Новий пароль має бути не коротший за 8 символів" };
  await db.update(users).set({ passwordHash: hashPassword(next) }).where(eq(users.id, me.id));
  return { ok: "Пароль змінено" };
}

/* ───────────────────────── Прогрес і нотатки ───────────────────────── */

export async function toggleDoneAction(lessonId: number, done: boolean) {
  const me = await requireUser();
  if (done) {
    await db.insert(lessonProgress).values({ userId: me.id, lessonId }).onConflictDoNothing();
  } else {
    await db.delete(lessonProgress).where(and(eq(lessonProgress.userId, me.id), eq(lessonProgress.lessonId, lessonId)));
  }
  refresh();
}

export async function saveNoteAction(lessonId: number, text: string) {
  const me = await requireUser();
  const value = text.slice(0, 20_000);
  if (!value.trim()) {
    await db.delete(lessonNotes).where(and(eq(lessonNotes.userId, me.id), eq(lessonNotes.lessonId, lessonId)));
    return;
  }
  await db
    .insert(lessonNotes)
    .values({ userId: me.id, lessonId, text: value })
    .onConflictDoUpdate({ target: [lessonNotes.userId, lessonNotes.lessonId], set: { text: value, updatedAt: new Date() } });
}

/* ───────────────────────── Предмети / курси ───────────────────────── */

export async function saveSubjectAction(f: FormData) {
  const me = await requireEditor();
  const id = int(f, "id");
  const kind = f.get("kind") === "course" ? "course" : "subject";
  const title = str(f, "title", 256);
  if (!title) throw new Error("Назва обов'язкова");
  const data = {
    kind,
    title,
    code: kind === "subject" ? str(f, "code", 32) : null,
    instructor: kind === "subject" ? str(f, "instructor", 256) : null,
    year: kind === "subject" ? int(f, "year") : null,
    term: kind === "subject" ? int(f, "term") : null,
    ects: kind === "subject" ? int(f, "ects") : null,
    provider: kind === "course" ? str(f, "provider", 128) : null,
    url: safeUrl(str(f, "url")),
    icon: str(f, "icon", 32) ?? "book",
    color: str(f, "color", 32) ?? "indigo",
    description: str(f, "description", 5000),
    updatedAt: new Date(),
  };
  let subjectId = id;
  if (id) {
    await db.update(subjects).set(data).where(eq(subjects.id, id));
  } else {
    const [row] = await db.insert(subjects).values({ ...data, createdBy: me.id }).returning({ id: subjects.id });
    subjectId = row.id;
  }
  refresh();
  redirect(`/subjects/${subjectId}`);
}

export async function setArchivedAction(id: number, archived: boolean) {
  await requireEditor();
  await db.update(subjects).set({ isArchived: archived, updatedAt: new Date() }).where(eq(subjects.id, id));
  refresh();
}

export async function deleteSubjectAction(id: number) {
  const me = await requireEditor();
  const [s] = await db.select().from(subjects).where(eq(subjects.id, id));
  if (!s || !canDelete(me, s.createdBy)) throw new Error("Видаляти може автор або адмін");
  await db.delete(subjects).where(eq(subjects.id, id));
  refresh();
  redirect(s.kind === "course" ? "/courses" : "/subjects");
}

/* ───────────────────────── Заняття ───────────────────────── */

export async function saveLessonAction(f: FormData) {
  const me = await requireEditor();
  const id = int(f, "id");
  const subjectId = int(f, "subjectId");
  const title = str(f, "title", 256);
  if (!title || !subjectId) throw new Error("Назва обов'язкова");
  const kind = str(f, "kind", 16) ?? "lecture";
  const summary = String(f.get("summary") ?? "").trim() || null;
  const heldOn = str(f, "heldOn", 10);

  const data = {
    kind,
    title,
    description: str(f, "description", 5000),
    videoUrl: safeUrl(str(f, "videoUrl")),
    heldOn: heldOn && /^\d{4}-\d{2}-\d{2}$/.test(heldOn) ? heldOn : null,
    updatedAt: new Date(),
  };

  let lessonId = id;
  if (id) {
    const [old] = await db.select().from(lessons).where(eq(lessons.id, id));
    const summaryChanged = (old?.summary ?? null) !== summary;
    await db
      .update(lessons)
      .set({
        ...data,
        ...(summaryChanged
          ? { summary, summarySource: summary ? "manual" : null, summaryBy: summary ? me.id : null, summaryUpdatedAt: summary ? new Date() : null }
          : {}),
      })
      .where(eq(lessons.id, id));
  } else {
    const [{ m }] = await db
      .select({ m: max(lessons.number) })
      .from(lessons)
      .where(and(eq(lessons.subjectId, subjectId), eq(lessons.kind, kind)));
    const [row] = await db
      .insert(lessons)
      .values({
        ...data,
        subjectId,
        number: (m ?? 0) + 1,
        summary,
        summarySource: summary ? "manual" : null,
        summaryBy: summary ? me.id : null,
        summaryUpdatedAt: summary ? new Date() : null,
        createdBy: me.id,
      })
      .returning({ id: lessons.id });
    lessonId = row.id;
  }
  refresh();
  redirect(`/lessons/${lessonId}`);
}

export async function deleteLessonAction(id: number) {
  const me = await requireEditor();
  const [l] = await db.select().from(lessons).where(eq(lessons.id, id));
  if (!l || !canDelete(me, l.createdBy)) throw new Error("Видаляти може автор або адмін");
  await db.delete(lessons).where(eq(lessons.id, id));
  refresh();
  redirect(`/subjects/${l.subjectId}`);
}

/* ───────────────────────── Матеріали (посилання) ───────────────────────── */

export async function addMaterialAction(f: FormData) {
  const me = await requireEditor();
  const subjectId = int(f, "subjectId");
  const lessonId = int(f, "lessonId");
  const url = safeUrl(str(f, "url"));
  if (!subjectId || !url) throw new Error("Вкажи коректне посилання");
  const title = str(f, "title", 256) ?? new URL(url).hostname;
  await db.insert(materials).values({ subjectId, lessonId, kind: "link", title, url, createdBy: me.id });
  refresh();
}

export async function deleteMaterialAction(id: number) {
  const me = await requireEditor();
  const [m] = await db.select().from(materials).where(eq(materials.id, id));
  if (!m || !canDelete(me, m.createdBy)) throw new Error("Видаляти може автор або адмін");
  await db.delete(materials).where(eq(materials.id, id));
  refresh();
}

/* ───────────────────────── Завдання ───────────────────────── */

export async function saveTaskAction(f: FormData) {
  const me = await requireEditor();
  const id = int(f, "id");
  const subjectId = int(f, "subjectId");
  const lessonId = int(f, "lessonId");
  const title = str(f, "title", 256);
  const kind = String(f.get("kind"));
  const content = String(f.get("content") ?? "");
  if (!subjectId || !title) throw new Error("Назва обов'язкова");
  if (!["html", "markdown", "python"].includes(kind)) throw new Error("Невідомий тип завдання");
  if (!content.trim()) throw new Error("Завдання порожнє");
  if (content.length > MAX_CONTENT) throw new Error("Файл завеликий (макс. 15 МБ)");

  const data = { title, kind, content, fileName: str(f, "fileName", 256), updatedAt: new Date() };
  let taskId = id;
  if (id) {
    await db.update(tasks).set(data).where(eq(tasks.id, id));
  } else {
    const [row] = await db.insert(tasks).values({ ...data, subjectId, lessonId, createdBy: me.id }).returning({ id: tasks.id });
    taskId = row.id;
  }
  refresh();
  redirect(`/tasks/${taskId}`);
}

export async function deleteTaskAction(id: number) {
  const me = await requireEditor();
  const [t] = await db.select().from(tasks).where(eq(tasks.id, id));
  if (!t || !canDelete(me, t.createdBy)) throw new Error("Видаляти може автор або адмін");
  await db.delete(tasks).where(eq(tasks.id, id));
  refresh();
  redirect(t.lessonId ? `/lessons/${t.lessonId}` : `/subjects/${t.subjectId}`);
}

/** Автозбереження особистої копії. */
export async function saveTaskWorkAction(taskId: number, content: string) {
  const me = await requireUser();
  if (content.length > MAX_CONTENT) throw new Error("Завелика копія");
  await db
    .insert(taskWork)
    .values({ userId: me.id, taskId, content })
    .onConflictDoUpdate({ target: [taskWork.userId, taskWork.taskId], set: { content, updatedAt: new Date() } });
}

/** Відкат до базової версії. */
export async function resetTaskWorkAction(taskId: number) {
  const me = await requireUser();
  await db.delete(taskWork).where(and(eq(taskWork.userId, me.id), eq(taskWork.taskId, taskId)));
  refresh();
}

/* ───────────────────────── Адмінка ───────────────────────── */

export async function createUserAction(_: FormState, f: FormData): Promise<FormState> {
  await requireAdmin();
  const tgId = int(f, "telegramId");
  const fullName = str(f, "fullName", 256);
  const login = (str(f, "login", 64) ?? "").toLowerCase();
  if (!tgId || tgId <= 0) return { error: "Вкажи числовий Telegram ID" };
  if (!/^[a-z0-9_.-]{3,64}$/.test(login)) return { error: "Логін: 3–64 символи, латиниця, цифри, _ . -" };
  const password = String(f.get("password") ?? "").trim() || generatePassword();
  if (password.length < 8) return { error: "Пароль має бути не коротший за 8 символів" };

  const [taken] = await db.select({ id: users.id }).from(users).where(eq(users.login, login));
  if (taken && taken.id !== tgId) return { error: "Цей логін уже зайнятий" };

  const values = {
    login,
    passwordHash: hashPassword(password),
    status: "active",
    canEdit: f.get("canEdit") === "on",
    ...(fullName ? { fullName } : {}),
  };
  await db
    .insert(users)
    .values({ id: tgId, fullName: fullName ?? login, ...values })
    .onConflictDoUpdate({ target: users.id, set: values });
  refresh();
  return { ok: `Користувача «${login}» збережено. Передай йому дані для входу:`, password, error: undefined };
}

export async function resetPasswordAction(userId: number): Promise<FormState> {
  await requireAdmin();
  const password = generatePassword();
  await db.update(users).set({ passwordHash: hashPassword(password) }).where(eq(users.id, userId));
  await db.delete(webSessions).where(eq(webSessions.userId, userId)); // вихід на всіх пристроях
  return { ok: "Новий пароль", password };
}

export async function setUserFlagsAction(userId: number, patch: { canEdit?: boolean; status?: "active" | "blocked" }) {
  const me = await requireAdmin();
  if (userId === me.id) throw new Error("Не можна змінювати власний доступ");
  await db.update(users).set(patch).where(eq(users.id, userId));
  if (patch.status === "blocked") await db.delete(webSessions).where(eq(webSessions.userId, userId));
  refresh();
}

export async function deleteUserAction(userId: number) {
  const me = await requireAdmin();
  if (userId === me.id) throw new Error("Не можна видалити себе");
  await db.delete(users).where(eq(users.id, userId));
  refresh();
}

export async function togglePythonExecutionAction(enabled: boolean) {
  await requireAdmin();
  updateAppSettings({ allowPythonExecution: enabled });
  refresh();
}

