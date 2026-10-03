"use client";

import { useActionState } from "react";
import { loginAction, setupAction } from "@/app/actions";
import { Button, Field, inputClass } from "@/components/ui";

function Err({ msg }: { msg?: string }) {
  return msg ? <p className="rounded-lg bg-red-bg px-3 py-2 text-xs text-red-fg">{msg}</p> : null;
}

export function LoginForm() {
  const [state, action, pending] = useActionState(loginAction, undefined);
  return (
    <form action={action} className="space-y-4">
      <Field label="Логін">
        <input name="login" autoComplete="username" autoCapitalize="none" autoFocus required className={inputClass} />
      </Field>
      <Field label="Пароль">
        <input name="password" type="password" autoComplete="current-password" required className={inputClass} />
      </Field>
      <Err msg={state?.error} />
      <Button variant="primary" className="w-full" disabled={pending}>
        {pending ? "Входимо…" : "Увійти"}
      </Button>
    </form>
  );
}

export function SetupForm() {
  const [state, action, pending] = useActionState(setupAction, undefined);
  return (
    <form action={action} className="space-y-4">
      <Field label="Ім'я">
        <input name="fullName" autoComplete="name" className={inputClass} />
      </Field>
      <Field label="Telegram ID" hint="Той самий, що ADMIN_ID у боті (бот відповідає на /id)">
        <input name="telegramId" inputMode="numeric" required className={inputClass} />
      </Field>
      <Field label="Логін">
        <input name="login" autoComplete="username" autoCapitalize="none" required className={inputClass} />
      </Field>
      <Field label="Пароль" hint="Щонайменше 8 символів">
        <input name="password" type="password" autoComplete="new-password" minLength={8} required className={inputClass} />
      </Field>
      <label className="flex items-center gap-2 text-sm text-muted">
        <input type="checkbox" name="demo" defaultChecked className="accent-[var(--accent)]" /> Додати демо-дані (предмети, заняття, приклади завдань)
      </label>
      <Err msg={state?.error} />
      <Button variant="primary" className="w-full" disabled={pending}>
        {pending ? "Створюємо…" : "Створити й увійти"}
      </Button>
    </form>
  );
}
