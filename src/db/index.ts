import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import * as schema from "./schema";

const defaultDbPath = fs.existsSync(path.join(process.cwd(), "data", "backnote.db"))
  ? path.join(process.cwd(), "data", "backnote.db")
  : fs.existsSync(path.join(process.cwd(), "sqlite.db"))
    ? path.join(process.cwd(), "sqlite.db")
    : path.join(process.cwd(), "data", "backnote.db");

const rawUrl = process.env.DATABASE_URL;
const dbPath = rawUrl
  ? rawUrl.replace(/^sqlite(\+aiosqlite)?:\/\/\/?/, "")
  : defaultDbPath;

// Переконатися, що папка для БД існує
fs.mkdirSync(path.dirname(dbPath), { recursive: true });

const globalForDb = globalThis as typeof globalThis & {
  __backnoteSqlite?: Database.Database;
};

const sqlite =
  globalForDb.__backnoteSqlite ??
  new Database(dbPath);

// Увімкнути foreign keys і WAL mode для кращої продуктивності
sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

if (process.env.NODE_ENV !== "production") {
  globalForDb.__backnoteSqlite = sqlite;
}

export const db = drizzle(sqlite, { schema });
export const rawSqlite = sqlite;
