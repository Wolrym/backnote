"""Fire-and-forget broadcasts to other members of the study base."""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backnote.bot.callbacks import OpenCb
from backnote.db.models import Lesson, Subject, User
from backnote.formatting import h, lesson_heading, lesson_kind
from backnote.services import Services

log = logging.getLogger(__name__)


def open_kb(target: str, obj_id: int, text: str = "Open") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=OpenCb(target=target, id=obj_id))
    return kb.as_markup()


class Notifier:
    def __init__(self, bot: Bot, services: Services, tz) -> None:
        self._bot = bot
        self._svc = services
        self._tz = tz
        self._tasks: set[asyncio.Task] = set()

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def send(self, chat_id: int, text: str, markup: InlineKeyboardMarkup | None) -> bool:
        try:
            await self._bot.send_message(chat_id, text, reply_markup=markup)
            return True
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            return await self.send(chat_id, text, markup)
        except TelegramForbiddenError:
            log.info("User %s blocked the bot", chat_id)
        except Exception:
            log.exception("Failed to notify %s", chat_id)
        return False

    async def _broadcast(self, author_id: int, text: str, markup: InlineKeyboardMarkup) -> None:
        for user_id in await self._svc.users.active_ids(
            exclude=author_id, setting="notify_new_content"
        ):
            await self.send(user_id, text, markup)
            await asyncio.sleep(0.05)

    def new_lesson(self, lesson: Lesson, subject: Subject, author: User | None) -> None:
        by = f"\n<i>added by {h(author.display_name)}</i>" if author else ""
        text = (
            f"🆕 <b>New {lesson_kind(lesson.kind).label.lower()}</b> in {h(subject.title)}\n"
            f"<blockquote>{h(lesson_heading(lesson))}"
            f"</blockquote>{by}"
        )
        self._spawn(
            self._broadcast(lesson.created_by or 0, text, open_kb("lesson", lesson.id, "▶️ Open"))
        )

    def run(self, coro) -> None:
        """Run an arbitrary background job (e.g. AI summary) and keep a reference to it."""
        self._spawn(coro)
