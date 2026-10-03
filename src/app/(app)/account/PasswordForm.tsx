"use client";

import { useActionState } from "react";
import { changePasswordAction } from "@/app/actions";
import { Button, Field, inputClass } from "@/components/ui";

export default function PasswordForm() {
  const [state, action, pending] = useActionState(changePasswordAction, undefined);
  return (
    <form action={action} className="space-y-4">
      <Field label="Поточний пароль">
        <input name="current" type="password" autoComplete="current-password" required className={inputClass} />
      </Field>
      <Field label="Новий пароль" hint="Щонайменше 8 символів">
        <input name="next" type="password" autoComplete="new-password" minLength={8} required className={inputClass} />
      </Field>
      {state?.error && <p className="rounded-lg bg-red-bg px-3 py-2 text-xs text-red-fg">{state.error}</p>}
      {state?.ok && <p className="rounded-lg bg-green-bg px-3 py-2 text-xs text-green-fg">{state.ok}</p>}
      <Button variant="primary" disabled={pending}>
        Зберегти
      </Button>
    </form>
  );
}
