import { Card, PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import PasswordForm from "./PasswordForm";

export default async function AccountPage() {
  const me = await requireUser();
  return (
    <div className="max-w-md">
      <PageHeader title="Мій акаунт" subtitle={`${me.fullName}${me.login ? ` · ${me.login}` : ""} · ${me.isAdmin ? "адмін" : me.canEdit ? "редактор" : "перегляд"}`} />
      <Card className="p-5">
        <h2 className="mb-4 text-sm font-medium">Змінити пароль</h2>
        <PasswordForm />
      </Card>
    </div>
  );
}
