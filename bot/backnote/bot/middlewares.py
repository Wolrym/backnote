"""Whitelist gate: only active members reach handlers; strangers can request access."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backnote.bot.callbacks import AccessCb
from backnote.db.models import User, UserStatus
from backnote.formatting import h
from backnote.services import Services

log = logging.getLogger(__name__)


def access_request_kb(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="Allow", callback_data=AccessCb(action="allow", user_id=user_id))
    kb.button(text="Block", callback_data=AccessCb(action="block", user_id=user_id))
    return kb.as_markup()


class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        chat = data.get("event_chat")
        if tg_user is None or tg_user.is_bot or (chat is not None and chat.type != "private"):
            return None

        svc: Services = data["svc"]
        user, created = await svc.users.touch(tg_user)
        data["db_user"] = user
        if user.status == UserStatus.ACTIVE:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer("You don't have access to this bot.", show_alert=True)
        elif isinstance(event, Message):
            await self._deny(event, user, created, data)
        return None

    async def _deny(self, message: Message, user: User, created: bool, data: dict) -> None:
        your_id = f"Your Telegram ID: <code>{user.id}</code>"
        if user.status == UserStatus.BLOCKED:
            await message.answer(f"Access denied.\n{your_id}")
            return
        if created:
            await self._notify_admin(message, user, data)
        await message.answer(
            "<b>Backnote</b> is a private study base.\n\n"
            "Your access request was sent to the admin — you'll get a message once it's "
            f"approved.\n\n{your_id}"
        )

    async def _notify_admin(self, message: Message, user: User, data: dict) -> None:
        admin_id = data["settings"].admin_id
        username = f" (@{h(user.username)})" if user.username else ""
        try:
            await message.bot.send_message(
                admin_id,
                f"<b>Access request</b>\n<blockquote>{h(user.display_name)}{username}\n"
                f"ID: <code>{user.id}</code></blockquote>",
                reply_markup=access_request_kb(user.id),
            )
        except Exception:
            log.exception("Could not notify admin about access request from %s", user.id)
