"use client";

import { Check, Copy, KeyRound, Pencil, Plus, Shield, ShieldOff, Trash2 } from "lucide-react";
import { useActionState, useState, useTransition } from "react";
import { createUserAction, deleteUserAction, resetPasswordAction, setUserFlagsAction, togglePythonExecutionAction, type FormState } from "@/app/actions";
import { Button, Field, inputClass } from "@/components/ui";

function Credentials({ login, password }: { login?: string; password: string }) {
  const [copied, setCopied] = useState(false);
  const line = login ? `Логін: ${login}\nПароль: ${password}` : password;
  return (
    <div className="mt-3 flex items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 py-2 font-mono text-xs">
      <div className="min-w-0 flex-1 whitespace-pre-wrap break-all">{line}</div>
      <button
        type="button"
        onClick={async () => {
          await navigator.clipboard.writeText(line);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
        className="cursor-pointer text-muted hover:text-fg"
        aria-label="Копіювати"
      >
        {copied ? <Check size={14} /> : <Copy size={14} />}
      </button>
    </div>
  );
}

export function UserForm({ telegramId, fullName, login, canEdit, compact }: { telegramId?: number; fullName?: string | null; login?: string | null; canEdit?: boolean; compact?: boolean }) {
  const [state, action, pending] = useActionState<FormState, FormData>(createUserAction, undefined);
  return (
    <form action={action} className={compact ? "space-y-3 px-4 pb-4" : "space-y-3"}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Telegram ID">
          <input name="telegramId" inputMode="numeric" required defaultValue={telegramId} readOnly={!!telegramId} className={inputClass} />
        </Field>
        <Field label="Ім'я">
          <input name="fullName" defaultValue={fullName ?? ""} className={inputClass} />
        </Field>
        <Field label="Логін">
          <input name="login" required autoCapitalize="none" defaultValue={login ?? ""} className={inputClass} />
        </Field>
        <Field label="Пароль" hint="Порожнє — згенерується автоматично">
          <input name="password" autoComplete="off" className={inputClass} />
        </Field>
      </div>
      <label className="flex items-center gap-2 text-sm text-muted">
        <input type="checkbox" name="canEdit" defaultChecked={canEdit} className="accent-[var(--accent)]" /> Редактор (може додавати й змінювати предмети, заняття, завдання)
      </label>
      {state?.error && <p className="rounded-lg bg-red-bg px-3 py-2 text-xs text-red-fg">{state.error}</p>}
      {state?.ok && (
        <div>
          <p className="text-xs text-green-fg">{state.ok}</p>
          {state.password && <Credentials login={undefined} password={state.password} />}
        </div>
      )}
      <Button variant="primary" disabled={pending}>
        <Plus size={14} /> {pending ? "Зберігаю…" : "Зберегти"}
      </Button>
    </form>
  );
}

export function UserActions({ id, canEdit, blocked, hasLogin, login }: { id: number; canEdit: boolean; blocked: boolean; hasLogin: boolean; login: string | null }) {
  const [pending, start] = useTransition();
  const [creds, setCreds] = useState<string | null>(null);

  return (
    <div>
      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="ghost"
          className={`h-9 px-2.5 text-xs ${canEdit ? "text-indigo-fg font-medium" : ""}`}
          disabled={pending}
          title={canEdit ? "Забрати права редактора" : "Дати права редактора"}
          onClick={() => start(() => setUserFlagsAction(id, { canEdit: !canEdit }))}
        >
          {canEdit ? <Shield size={16} /> : <ShieldOff size={16} />}
          <span className="hidden sm:inline">{canEdit ? "Редактор" : "Перегляд"}</span>
        </Button>
        {hasLogin && (
          <Button
            variant="ghost"
            className="h-9 w-9 px-0"
            disabled={pending}
            title="Згенерувати новий пароль"
            aria-label="Новий пароль"
            onClick={() =>
              start(async () => {
                if (!confirm("Згенерувати новий пароль? Користувача буде розлогінено на всіх пристроях.")) return;
                const r = await resetPasswordAction(id);
                setCreds(r?.password ?? null);
              })
            }
          >
            <KeyRound size={16} />
          </Button>
        )}
        <Button
          variant="ghost"
          className="h-9 px-2.5 text-xs"
          disabled={pending}
          onClick={() => start(() => setUserFlagsAction(id, { status: blocked ? "active" : "blocked" }))}
        >
          {blocked ? "Розблокувати" : "Заблокувати"}
        </Button>
        <Button
          variant="danger"
          className="h-9 w-9 px-0"
          disabled={pending}
          aria-label="Видалити"
          title="Видалити"
          onClick={() => confirm("Видалити користувача разом з його прогресом і нотатками?") && start(() => deleteUserAction(id))}
        >
          <Trash2 size={16} />
        </Button>
      </div>
      {creds && (
        <div className="absolute right-4 mt-1 z-10 w-64 rounded-lg border border-line bg-surface p-3 shadow-lg">
          <div className="text-xs text-muted">Новий пароль{login ? ` для ${login}` : ""}:</div>
          <Credentials password={creds} />
          <button className="mt-2 cursor-pointer text-xs text-muted hover:text-fg" onClick={() => setCreds(null)}>
            Закрити
          </button>
        </div>
      )}
    </div>
  );
}

export function EditIcon() {
  return <Pencil size={14} />;
}

export function SecuritySettings({ initialAllowPython }: { initialAllowPython: boolean }) {
  const [allow, setAllow] = useState(initialAllowPython);
  const [pending, start] = useTransition();

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="max-w-xl">
        <div className="text-sm font-medium">Виконання Python у браузері</div>
        <div className="mt-0.5 text-xs text-muted">
          Дозволяє користувачам запускати код на сторінці завдань. Якщо вимкнено — запуск заблоковано для безпеки, Python-файли відкриваються лише для читання та редагування.
        </div>
      </div>
      <Button
        variant={allow ? "secondary" : "danger"}
        disabled={pending}
        onClick={() => {
          const next = !allow;
          setAllow(next);
          start(async () => {
            await togglePythonExecutionAction(next);
          });
        }}
        className="shrink-0"
      >
        {pending ? "Збереження…" : allow ? "✓ Дозволено (активно)" : "🔒 Вимкнено (лише читання)"}
      </Button>
    </div>
  );
}

