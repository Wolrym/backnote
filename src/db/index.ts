import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import fs from "node:fs";
import path from "node:path";
import * as schema from "./schema";

function resolveDbPath(raw?: string): string {
  if (!raw) {
    if (fs.existsSync(path.join(process.cwd(), "data", "backnote.db"))) {
      return path.join(process.cwd(), "data", "backnote.db");
    }
    if (fs.existsSync(path.join(process.cwd(), "sqlite.db"))) {
      return path.join(process.cwd(), "sqlite.db");
    }
    return path.join(process.cwd(), "data", "backnote.db");
  }
  // sqlite:////app/data/backnote.db (4 слеші: абсолютний шлях /app/data/backnote.db)
  if (raw.startsWith("sqlite:////")) {
    return raw.slice("sqlite:///".length);
  }
  // sqlite:///app/data/backnote.db (3 слеші: якщо починається на /app, то абсолютний)
  if (raw.startsWith("sqlite:///app/")) {
    return raw.slice("sqlite://".length);
  }
  // Інші sqlite:///path відносні
  const cleaned = raw.replace(/^sqlite(?:\+aiosqlite)?:\/\/\/?/, "");
  return path.isAbsolute(cleaned) ? cleaned : path.resolve(process.cwd(), cleaned);
}

const dbPath = resolveDbPath(process.env.DATABASE_URL);

// Переконатися, що папка для БД існує
try {
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
} catch {
  /* ігноруємо, якщо папка вже є або немає прав на створення батьківських */
}

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
