import { redirect } from "next/navigation";
import { Avatar, Badge, Card, PageHeader, SectionTitle } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { listUsers } from "@/lib/data";
import { getAppSettings } from "@/lib/settings";
import { SecuritySettings, UserActions, UserForm } from "./AdminClient";

export default async function AdminPage() {
  const me = await requireUser();
  if (!me.isAdmin) redirect("/");
  const all = await listUsers();
  const needAccess = all.filter((u) => !u.login && !u.isAdmin); // зайшли через бота, ще без доступу на сайт
  const members = all.filter((u) => u.login || u.isAdmin);
  const settings = getAppSettings();

  return (
    <div className="w-full space-y-8">
      <PageHeader title="Учасники та налаштування" subtitle="Керування доступом до сайту, правами та безпекою" />

      <section>
        <SectionTitle>Безпека та виконання коду</SectionTitle>
        <Card className="p-5">
          <SecuritySettings initialAllowPython={settings.allowPythonExecution} />
        </Card>
      </section>

      <section>
        <SectionTitle>Додати користувача</SectionTitle>
        <Card className="p-5">
          <UserForm />
        </Card>
      </section>

      {needAccess.length > 0 && (
        <section className="mb-8">
          <SectionTitle>
            Є в боті, але без доступу на сайт <Badge tone="amber">{needAccess.length}</Badge>
          </SectionTitle>
          <Card className="divide-y divide-line overflow-hidden">
            {needAccess.map((u) => (
              <details key={u.id}>
                <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 transition hover:bg-surface-2/60 [&::-webkit-details-marker]:hidden">
                  <Avatar name={u.fullName ?? u.username ?? "?"} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{u.fullName ?? u.username ?? u.id}</div>
                    <div className="text-xs text-faint">
                      {u.username ? `@${u.username} · ` : ""}
                      {u.id}
                    </div>
                  </div>
                  <span className="text-xs text-muted">Створити вхід →</span>
                </summary>
                <UserForm compact telegramId={u.id} fullName={u.fullName} login={u.username?.toLowerCase()} />
              </details>
            ))}
          </Card>
        </section>
      )}

      <section>
        <SectionTitle>Користувачі сайту ({members.length})</SectionTitle>
        <Card className="relative divide-y divide-line">
          {members.map((u) => (
            <div key={u.id} className="flex items-center gap-3 px-4 py-3">
              <Avatar name={u.fullName ?? u.login ?? "?"} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium">
                  <span className="truncate">{u.fullName ?? u.login}</span>
                  {u.isAdmin && <Badge tone="indigo">Адмін</Badge>}
                  {!u.isAdmin && u.canEdit && <Badge tone="green">Редактор</Badge>}
                  {u.status === "blocked" && <Badge tone="red">Заблоковано</Badge>}
                </div>
                <div className="truncate text-xs text-faint">
                  {u.login} · TG {u.id}
                  {u.lastSeenAt ? ` · заходив ${u.lastSeenAt.toLocaleDateString("uk-UA")}` : ""}
                </div>
              </div>
              {u.id !== me.id && <UserActions id={u.id} canEdit={u.canEdit} blocked={u.status === "blocked"} hasLogin={!!u.login} login={u.login} />}
            </div>
          ))}
        </Card>
      </section>
    </div>
  );
}
