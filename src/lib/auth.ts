import { createHash, randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";
import { eq } from "drizzle-orm";
import { db } from "@/db";
import { users, webSessions } from "@/db/schema";

const COOKIE = "bn_session";
const SESSION_DAYS = 60; // «запам'ятати мене» — користувач не вводить пароль щоразу
const DAY = 86_400_000;

export type SessionUser = {
  id: number;
  fullName: string;
  username: string | null;
  login: string | null;
  isAdmin: boolean;
  canEdit: boolean;
};

export function hashPassword(password: string): string {
  const salt = randomBytes(16);
  const hash = scryptSync(password, salt, 64);
  return `scrypt$${salt.toString("hex")}$${hash.toString("hex")}`;
}

export function verifyPassword(password: string, stored: string | null): boolean {
  if (!stored) return false;
  const [scheme, saltHex, hashHex] = stored.split("$");
  if (scheme !== "scrypt" || !saltHex || !hashHex) return false;
  const expected = Buffer.from(hashHex, "hex");
  const actual = scryptSync(password, Buffer.from(saltHex, "hex"), expected.length);
  return timingSafeEqual(expected, actual);
}

export function generatePassword(): string {
  const alphabet = "abcdefghjkmnpqrstuvwxyzACDEFGHJKLMNPQRSTUVWXYZ23456789";
  const bytes = randomBytes(12);
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
}

const sha = (token: string) => createHash("sha256").update(token).digest("hex");

export async function createSession(userId: number) {
  const token = randomBytes(32).toString("base64url");
  const expiresAt = new Date(Date.now() + SESSION_DAYS * DAY);
  await db.insert(webSessions).values({ id: sha(token), userId, expiresAt });
  const proto = (await headers()).get("x-forwarded-proto");
  (await cookies()).set(COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: proto === "https",
    path: "/",
    expires: expiresAt,
  });
}

export async function destroySession() {
  const jar = await cookies();
  const token = jar.get(COOKIE)?.value;
  if (token) await db.delete(webSessions).where(eq(webSessions.id, sha(token)));
  jar.delete(COOKIE);
}

/** Поточний користувач або null. Кешується на час одного запиту. */
export const getUser = cache(async (): Promise<SessionUser | null> => {
  const token = (await cookies()).get(COOKIE)?.value;
  if (!token) return null;
  const [row] = await db
    .select({ user: users, expiresAt: webSessions.expiresAt })
    .from(webSessions)
    .innerJoin(users, eq(users.id, webSessions.userId))
    .where(eq(webSessions.id, sha(token)))
    .limit(1);
  if (!row || row.expiresAt.getTime() < Date.now() || row.user.status !== "active") return null;
  const u = row.user;
  return {
    id: u.id,
    fullName: u.fullName || u.username || String(u.id),
    username: u.username,
    login: u.login,
    isAdmin: u.isAdmin,
    canEdit: u.isAdmin || u.canEdit,
  };
});

export async function requireUser(): Promise<SessionUser> {
  const user = await getUser();
  if (!user) redirect("/login");
  return user;
}

export async function requireEditor(): Promise<SessionUser> {
  const user = await requireUser();
  if (!user.canEdit) throw new Error("Немає прав редактора");
  return user;
}

export async function requireAdmin(): Promise<SessionUser> {
  const user = await requireUser();
  if (!user.isAdmin) throw new Error("Лише для адміна");
  return user;
}
