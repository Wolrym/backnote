"""Sending long formatted documents with Bot API 10 Rich Messages, with a plain-text fallback."""

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InputRichMessage

from backnote.formatting import split_text

log = logging.getLogger(__name__)

RICH_LIMIT = 32_000


async def send_markdown(
    bot: Bot,
    chat_id: int,
    markdown: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if len(markdown) <= RICH_LIMIT:
        try:
            await bot.send_rich_message(
                chat_id=chat_id,
                rich_message=InputRichMessage(markdown=markdown),
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest as exc:
            log.warning("Rich message rejected, falling back to plain text: %s", exc)
    chunks = split_text(markdown)
    for i, chunk in enumerate(chunks):
        await bot.send_message(
            chat_id,
            chunk,
            parse_mode=None,
            reply_markup=reply_markup if i == len(chunks) - 1 else None,
        )
