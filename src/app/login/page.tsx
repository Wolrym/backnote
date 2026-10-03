import { BookOpen } from "lucide-react";
import { redirect } from "next/navigation";
import { eq, sql } from "drizzle-orm";
import { db } from "@/db";
import { users } from "@/db/schema";
import { getUser } from "@/lib/auth";
import ThemeToggle from "@/components/ThemeToggle";
import { LoginForm, SetupForm } from "./forms";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  if (await getUser()) redirect("/");
  const [{ n }] = await db.select({ n: sql<number>`cast(count(*) as integer)` }).from(users).where(eq(users.isAdmin, true));
  const setup = n === 0;

  return (
    <main className="relative grid min-h-screen place-items-center px-5 py-10">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <div className="rise w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-accent text-accent-fg shadow-sm">
            <BookOpen size={20} />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">{setup ? "Перший запуск" : "Backnote"}</h1>
          <p className="mt-1 text-sm text-muted">
            {setup ? "Створи акаунт адміністратора — далі додаватимеш інших з адмінки." : "Увійди, щоб відкрити навчальну базу"}
          </p>
        </div>
        <div className="rounded-xl border border-line bg-surface p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
          {setup ? <SetupForm /> : <LoginForm />}
        </div>
        {!setup && <p className="mt-4 text-center text-xs text-faint">Немає доступу? Напиши адміну — він створить тобі акаунт. Після входу сесія запам'ятовується на 60 днів.</p>}
      </div>
    </main>
  );
}
