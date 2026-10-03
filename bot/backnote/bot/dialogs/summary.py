import logging

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from backnote.ai import SummaryError
from backnote.bot.dialogs.common import (
    BACK,
    CANCEL,
    DANGER,
    PRIMARY,
    copy_start_data,
    data_id,
    notifier,
    resend,
    settings,
    summarizer,
    svc,
    uid,
)
from backnote.bot.dialogs.states import SummarySG
from backnote.bot.notifier import open_kb
from backnote.bot.rich import send_markdown
from backnote.db.models import SummarySource
from backnote.formatting import (
    fmt_datetime,
    h,
    lesson_heading,
    summary_markdown,
    youtube_watch_url,
)
from backnote.services import Services

log = logging.getLogger(__name__)

MAX_FILE_BYTES = 512 * 1024

# Lessons with an AI job in flight (per process; good enough for a single bot instance).
GENERATING: set[int] = set()


async def send_summary(bot: Bot, svc_: Services, tz, chat_id: int, lesson_id: int) -> bool:
    lesson = await svc_.lessons.get(lesson_id)
    if lesson is None or not lesson.summary:
        return False
    subject = await svc_.subjects.get(lesson.subject_id)
    source = (
        "✨ AI-generated with Gemini" if lesson.summary_source == SummarySource.AI else "✍️ Written"
    )
    author = await svc_.users.get(lesson.summary_by) if lesson.summary_by else None
    parts = [source]
    if author and lesson.summary_source != SummarySource.AI:
        parts.append(f"by {author.display_name}")
    if lesson.summary_updated_at:
        parts.append(fmt_datetime(lesson.summary_updated_at, tz))
    await send_markdown(
        bot, chat_id, summary_markdown(lesson, subject, source_line=" · ".join(parts))
    )
    return True


async def main_getter(dialog_manager: DialogManager, **_):
    s = svc(dialog_manager)
    lesson = await s.lessons.get(data_id(dialog_manager, "lesson_id"))
    tz = settings(dialog_manager).tz
    ai_ready = summarizer(dialog_manager) is not None
    youtube = youtube_watch_url(lesson.video_url)
    generating = lesson.id in GENERATING

    lines = [f"🧠 <b>Summary</b> · {h(lesson_heading(lesson))}"]
    if lesson.summary:
        source = "✨ AI-generated" if lesson.summary_source == SummarySource.AI else "✍️ Written"
        updated = fmt_datetime(lesson.summary_updated_at, tz) if lesson.summary_updated_at else ""
        preview = lesson.summary.strip()
        if len(preview) > 600:
            preview = preview[:600].rsplit(" ", 1)[0] + " …"
        lines.append(
            f"<blockquote>{source} · {updated} · {len(lesson.summary):,} chars</blockquote>"
        )
        lines.append(f"<blockquote expandable>{h(preview)}</blockquote>")
        lines.append("<i>Tap “Read” to open it with full formatting.</i>")
    else:
        lines.append(
            "\n<blockquote>No summary yet.\nWrite one yourself — Markdown works: headings, "
            "lists, tables, $formulas$, spoilers.</blockquote>"
        )
    if generating:
        lines.append("\n<b>AI is watching the lecture…</b> I'll message you when it's done.")
    elif not ai_ready:
        lines.append(
            "\n<i>AI summaries are off. The admin can enable them with a free GEMINI_API_KEY.</i>"
        )
    elif not youtube:
        lines.append("\n<i>AI summaries need a public YouTube recording link.</i>")
    return {
        "text": "\n".join(lines),
        "has_summary": bool(lesson.summary),
        "can_generate": ai_ready and bool(youtube) and not generating,
        "write_label": "✍️ Replace" if lesson.summary else "✍️ Write",
        "ai_label": "✨ Regenerate with AI" if lesson.summary else "✨ Generate with AI",
    }


async def on_read(callback: CallbackQuery, _b, manager: DialogManager) -> None:
    await send_summary(
        callback.bot,
        svc(manager),
        settings(manager).tz,
        callback.message.chat.id,
        data_id(manager, "lesson_id"),
    )
    resend(manager)


async def _generate(
    bot: Bot, s: Services, tz, gemini, lesson_id: int, user_id: int, chat_id: int
) -> None:
    try:
        lesson = await s.lessons.get(lesson_id)
        subject = await s.subjects.get(lesson.subject_id)
        text = await gemini.summarize_video(
            youtube_watch_url(lesson.video_url),
            title=lesson.title,
            subject=subject.title,
            kind=lesson.kind,
        )
        await s.lessons.set_summary(lesson_id, text, SummarySource.AI, user_id)
        await bot.send_message(
            chat_id,
            f"<b>Summary ready</b>\n<blockquote>{h(lesson_heading(lesson))}</blockquote>",
            reply_markup=open_kb("summary", lesson_id, "Read summary"),
        )
    except SummaryError as exc:
        await bot.send_message(chat_id, f"⚠️ Could not generate the summary:\n<i>{h(exc)}</i>")
    except Exception:
        log.exception("AI summary failed for lesson %s", lesson_id)
        await bot.send_message(chat_id, "⚠️ Could not generate the summary (unexpected error).")
    finally:
        GENERATING.discard(lesson_id)


async def on_generate(callback: CallbackQuery, _b, manager: DialogManager) -> None:
    gemini = summarizer(manager)
    lesson_id = data_id(manager, "lesson_id")
    if gemini is None or lesson_id in GENERATING:
        return
    GENERATING.add(lesson_id)
    notifier(manager).run(
        _generate(
            callback.bot,
            svc(manager),
            settings(manager).tz,
            gemini,
            lesson_id,
            uid(manager),
            callback.message.chat.id,
        )
    )
    await callback.answer("Started. Long lectures can take a few minutes.")


async def on_input(message: Message, _w, manager: DialogManager) -> None:
    if message.document:
        doc = message.document
        if (doc.file_size or 0) > MAX_FILE_BYTES:
            await message.answer("⚠️ The file is too large (max 512 KB of text).")
            return
        buffer = await message.bot.download(doc)
        try:
            text = buffer.read().decode("utf-8")
        except UnicodeDecodeError:
            await message.answer("⚠️ Send a UTF-8 text file (.md or .txt).")
            return
    else:
        text = message.text or ""
    text = text.strip()
    if not text:
        await message.answer("⚠️ The summary is empty.")
        return
    await svc(manager).lessons.set_summary(
        data_id(manager, "lesson_id"), text, SummarySource.MANUAL, uid(manager)
    )
    await manager.switch_to(SummarySG.main)


async def on_delete(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await svc(manager).lessons.set_summary(data_id(manager, "lesson_id"), None, None, None)
    await manager.switch_to(SummarySG.main)


def summary_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{text}"),
            Button(
                Const("📖 Read"), id="read", on_click=on_read, when="has_summary", style=PRIMARY
            ),
            Button(Format("{ai_label}"), id="ai", on_click=on_generate, when="can_generate"),
            Row(
                SwitchTo(Format("{write_label}"), id="write", state=SummarySG.input),
                SwitchTo(
                    Const("🗑 Delete"), id="delete", state=SummarySG.delete, when="has_summary"
                ),
            ),
            Cancel(BACK),
            state=SummarySG.main,
            getter=main_getter,
        ),
        Window(
            Const(
                "<b>Write the summary</b>\n\nSend it as a message or as a <b>.md / .txt</b> file "
                "(for long notes). Markdown is supported:\n"
                "<blockquote expandable>## Heading\n- bullet, 1. numbered\n**bold**, *italic*, "
                "==highlight==\n| Term | Meaning |\n|---|---|\n| GDP | Gross domestic product |\n"
                "$MC = MR$ or $$\\frac{dy}{dx}$$\n"
                "&lt;details&gt;&lt;summary&gt;Answer&lt;/summary&gt;…&lt;/details&gt;</blockquote>"
            ),
            MessageInput(on_input, content_types=["text", "document"]),
            SwitchTo(CANCEL, id="cancel", state=SummarySG.main),
            state=SummarySG.input,
        ),
        Window(
            Const("🗑 Delete this summary for everyone?"),
            Row(
                Button(Const("🗑 Yes, delete"), id="confirm", on_click=on_delete, style=DANGER),
                SwitchTo(CANCEL, id="cancel", state=SummarySG.main),
            ),
            state=SummarySG.delete,
        ),
        on_start=copy_start_data,
    )
