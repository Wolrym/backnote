"""End-to-end dialog flows using aiogram-dialog's offline test tools."""

from typing import Any

import pytest
from aiogram.methods import TelegramMethod
from aiogram_dialog.test_tools import BotClient, MockMessageManager
from aiogram_dialog.test_tools.bot_client import FakeBot
from aiogram_dialog.test_tools.keyboard import InlineButtonTextLocator
from aiogram_dialog.test_tools.memory_storage import JsonMemoryStorage

from backnote.bot.factory import build_dispatcher
from backnote.bot.notifier import Notifier
from backnote.config import Settings
from backnote.db.models import UserStatus
from tests.conftest import ADMIN_ID


class RecordingBot(FakeBot):
    """FakeBot that records outgoing API calls instead of failing on them."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod] = []

    async def __call__(self, method: TelegramMethod[Any], request_timeout: int | None = None):
        self.calls.append(method)
        return True

    def texts(self) -> list[str]:
        return [getattr(c, "text", "") or "" for c in self.calls]


@pytest.fixture
def env(svc):
    settings = Settings(bot_token="1:x", admin_id=ADMIN_ID, _env_file=None)
    bot = RecordingBot()
    mm = MockMessageManager()
    dp = build_dispatcher(
        settings,
        svc,
        Notifier(bot, svc, settings.tz),
        bot_username="backnote_bot",
        storage=JsonMemoryStorage(),
        message_manager=mm,
    )
    admin = BotClient(dp, user_id=ADMIN_ID, chat_id=ADMIN_ID, bot=bot)
    return dp, bot, mm, admin


async def click(client: BotClient, mm: MockMessageManager, pattern: str) -> str:
    """Click a button whose text contains `pattern` (regex); `^...$` means an exact match."""
    if not pattern.startswith("^"):
        pattern = f".*{pattern}.*"
    await client.click(mm.last_message(), InlineButtonTextLocator(pattern.strip("^$")))
    return mm.last_message().text


async def test_stranger_requests_access(env, svc):
    dp, bot, mm, _ = env
    stranger = BotClient(dp, user_id=77, chat_id=77, bot=bot)
    await stranger.send("/start")
    assert (await svc.users.get(77)).status == UserStatus.PENDING
    assert any("Access request" in t for t in bot.texts())  # admin notified
    assert any("request was sent" in t for t in bot.texts())
    assert not mm.sent_messages  # no dialog for strangers


async def test_full_study_flow(env, svc):
    _, bot, mm, admin = env
    await admin.send("/start")
    assert "Backnote" in mm.last_message().text

    await click(admin, mm, "Subjects")
    await click(admin, mm, "Add subject")
    await admin.send("Microeconomics I")
    await click(admin, mm, r"^Year 1$")
    text = await click(admin, mm, r"^T3$")
    assert "Year 1 · Term 3" in text
    await click(admin, mm, "Next")
    text = await click(admin, mm, "Skip & create")
    assert "Microeconomics I" in text and "Year 1 · Term 3" in text

    await click(admin, mm, r"Lessons \(0\)")
    await click(admin, mm, "Add lesson")
    await click(admin, mm, "Lecture")
    await click(admin, mm, "Lecture 1")
    await admin.send("Supply & demand")
    await admin.send("Recording: https://youtu.be/dQw4w9WgXcQ")
    text = mm.last_message().text
    assert "Lecture 1 · Supply &amp; demand" in text
    assert "Not completed" in text

    text = await click(admin, mm, "Mark as completed")
    assert "Completed" in text and "Not completed" not in text

    await click(admin, mm, "Summary")
    await click(admin, mm, "Write")
    await admin.send("## Key ideas\n- Demand slopes down\n$P = a - bQ$")
    text = mm.last_message().text
    assert "Written" in text

    await click(admin, mm, "Read")
    rich = [c for c in bot.calls if type(c).__name__ == "SendRichMessage"]
    assert rich and "# 🎓 Lecture 1" in rich[-1].rich_message.markdown
    assert "$P = a - bQ$" in rich[-1].rich_message.markdown

    await click(admin, mm, "Back")
    await click(admin, mm, "My note")
    await admin.send("Re-watch from 12:00")
    assert "You have a note" in mm.last_message().text

    lessons = await svc.lessons.search("Supply")
    assert lessons[0][0].video_url == "https://youtu.be/dQw4w9WgXcQ"


async def test_course_and_new_lesson_notification(env, svc):
    import asyncio

    _, bot, mm, admin = env
    await svc.users.allow(3000)
    await admin.send("/start")
    await click(admin, mm, "Courses")
    await click(admin, mm, "Add course")
    await admin.send("Machine Learning")
    await admin.send("coursera.org/learn/machine-learning")
    text = await click(admin, mm, "Skip & create")
    assert "Machine Learning" in text

    await click(admin, mm, r"Lessons \(0\)")
    await click(admin, mm, "Add lesson")
    await click(admin, mm, "^Video$")
    await click(admin, mm, "Video 1")
    await admin.send("Gradient descent")
    await click(admin, mm, "No recording")
    assert "Video 1 · Gradient descent" in mm.last_message().text

    await asyncio.sleep(0.2)  # let the background broadcast run
    notes = [c for c in bot.calls if getattr(c, "chat_id", None) == 3000]
    assert notes and "New video" in notes[-1].text


async def test_deep_link_opens_lesson(env, svc):
    _, _, mm, admin = env
    from backnote.db.models import LessonKind, SubjectKind

    subject = await svc.subjects.create(kind=SubjectKind.SUBJECT, title="Stats", created_by=None)
    lesson = await svc.lessons.create(
        subject_id=subject.id, number=4, kind=LessonKind.SEMINAR, title="CLT", created_by=None
    )
    await admin.send(f"/start l{lesson.id}")
    assert "Seminar 4 · CLT" in mm.last_message().text
    text = await click(admin, mm, "All lessons")
    assert "Stats" in text


async def send_document(client: BotClient, file_name: str, caption: str | None = None) -> None:
    from datetime import datetime

    from aiogram.types import Document, Message, Update

    message = Message(
        message_id=client._new_message_id(),
        date=datetime.now(),
        chat=client.chat,
        from_user=client.user,
        document=Document(file_id=f"id-{file_name}", file_unique_id=file_name, file_name=file_name),
        caption=caption,
    )
    await client.dp.feed_update(
        client.bot, Update(update_id=client._new_update_id(), message=message)
    )


async def test_ui_tour(env, svc):
    """Walk through secondary windows to make sure every getter renders."""
    _, bot, mm, admin = env
    from backnote.db.models import LessonKind, SubjectKind

    await admin.send("/start")  # registers the admin
    subject = await svc.subjects.create(
        kind=SubjectKind.SUBJECT, title="Calculus", created_by=ADMIN_ID
    )
    await svc.lessons.create(
        subject_id=subject.id,
        number=1,
        kind=LessonKind.LECTURE,
        title="Limits",
        created_by=ADMIN_ID,
    )
    await admin.send("/start")

    # Settings toggle persists.
    await click(admin, mm, "Settings")
    text = await click(admin, mm, "New lessons")
    assert (await svc.users.get(ADMIN_ID)).notify_new_content is False
    await click(admin, mm, "Back")
    assert "Your progress" in await click(admin, mm, "Progress")
    await click(admin, mm, "Back")
    assert "How Backnote works" in await click(admin, mm, "Help")
    await click(admin, mm, "Show Markdown example")
    rich = [c for c in bot.calls if type(c).__name__ == "SendRichMessage"]
    assert "| Model | Parallel | Long context |" in rich[-1].rich_message.markdown
    await click(admin, mm, "Back")

    # Search -> lesson.
    await click(admin, mm, "Search")
    await admin.send("limit")
    text = await click(admin, mm, "Limits")
    assert "Lecture 1 · Limits" in text

    # Edit lesson fields.
    await click(admin, mm, "Edit")
    await click(admin, mm, "Title")
    await admin.send("Limits and continuity")
    await click(admin, mm, "Date")
    await click(admin, mm, "Today")
    await click(admin, mm, "Type")
    await click(admin, mm, "Seminar")
    await click(admin, mm, "Number")
    await admin.send("abc")
    assert any("whole number" in t for t in bot.texts())
    await admin.send("2")
    text = await click(admin, mm, "Back")
    assert "Seminar 2 · Limits and continuity" in text and "Calculus · " in text

    # Materials: a file and a link.
    await click(admin, mm, r"Materials \(0\)")
    await click(admin, mm, "Add")
    await send_document(admin, "slides.pdf")
    await admin.send("Extra reading https://example.com/book")
    text = mm.last_message().text
    assert "Added 2 item(s)" in text and "Extra reading" in text
    await click(admin, mm, "Rename last")
    await admin.send("Textbook")
    text = await click(admin, mm, "Done")
    assert "Materials" in text
    await click(admin, mm, "slides.pdf")
    assert any(type(c).__name__ == "SendDocument" for c in bot.calls)
    assert "slides.pdf" in mm.last_message().text
    await click(admin, mm, "Back")
    text = await click(admin, mm, "Textbook")
    assert "https://example.com/book" in text
    await click(admin, mm, "Delete")
    text = await click(admin, mm, "Yes, delete")
    assert "Textbook" not in str(mm.last_message().reply_markup)
    await click(admin, mm, "Back")

    # Subject edit + term + archive.
    await click(admin, mm, "All lessons")
    assert "Results for" in await click(admin, mm, "Back")  # back to the search it came from
    await admin.send("/start")
    await click(admin, mm, "Subjects")
    text = await click(admin, mm, "Calculus")
    assert "Calculus" in text
    await click(admin, mm, "Edit")
    await click(admin, mm, "ECTS")
    await admin.send("5")
    await click(admin, mm, "Year & term")
    await click(admin, mm, "^Year 2$")
    await click(admin, mm, "^T1$")
    await click(admin, mm, "Done")
    text = await click(admin, mm, "Archive")
    assert "archived" in text and "5 ECTS" in text and "Year 2 · Term 1" in text

    # Admin panel.
    await admin.send("/start")
    await click(admin, mm, "Admin")
    await click(admin, mm, "Add member")
    await admin.send("4242")
    text = mm.last_message().text
    assert "4242" in text and "active" in text
    await click(admin, mm, "Block")
    assert (await svc.users.get(4242)).status == UserStatus.BLOCKED
    await click(admin, mm, "Back")
    await click(admin, mm, "Back")
    await click(admin, mm, "Broadcast")
    await admin.send("Exam on Friday")
    text = await click(admin, mm, "Send")
    assert "Admin panel" in text


async def test_help_and_notification_buttons(env, svc):
    from datetime import datetime

    from aiogram.types import Message

    from backnote.bot.notifier import open_kb
    from backnote.db.models import LessonKind, SubjectKind

    _, bot, mm, admin = env
    await admin.send("/help")
    assert "How Backnote works" in mm.last_message().text

    subject = await svc.subjects.create(kind=SubjectKind.SUBJECT, title="Law", created_by=None)
    lesson = await svc.lessons.create(
        subject_id=subject.id, number=1, kind=LessonKind.LECTURE, title="Torts", created_by=None
    )
    await svc.lessons.set_summary(lesson.id, "**Duty of care**", "manual", ADMIN_ID)

    def notification(target: str) -> Message:
        return Message(
            message_id=999,
            date=datetime.now(),
            chat=admin.chat,
            text="🆕",
            reply_markup=open_kb(target, lesson.id),
        )

    await admin.click(notification("summary"), InlineButtonTextLocator("Open"))
    rich = [c for c in bot.calls if type(c).__name__ == "SendRichMessage"]
    assert "**Duty of care**" in rich[-1].rich_message.markdown

    await admin.click(notification("lesson"), InlineButtonTextLocator("Open"))
    assert "Lecture 1 · Torts" in mm.last_message().text
    # Back from a lesson opened via notification leads to its subject's lessons, then the menu.
    await click(admin, mm, "All lessons")
    assert "Backnote" in await click(admin, mm, "Back")


async def test_stale_button_restarts_the_menu(env, svc):
    """A button from a dialog created before a restart must not raise; the menu is re-sent."""
    from datetime import datetime

    from aiogram.types import CallbackQuery, ErrorEvent, Message, Update
    from aiogram_dialog.api.exceptions import UnknownIntent

    from backnote.bot.dialogs.states import MainSG
    from backnote.bot.handlers import on_stale_dialog

    _, bot, _, admin = env
    await admin.send("/start")

    class FakeBgManager:
        def __init__(self) -> None:
            self.started: list = []

        async def start(self, state, **kwargs):
            self.started.append(state)

    class FakeBgFactory:
        def __init__(self) -> None:
            self.manager = FakeBgManager()

        def bg(self, **kwargs):
            return self.manager

    stale = Message(
        message_id=90,
        date=datetime.now(),
        chat=admin.chat,
        from_user=admin.user,
        text="old menu",
    )
    callback = CallbackQuery(
        id="stale",
        chat_instance="-",
        from_user=admin.user,
        message=stale,
        data="aiogd_update::nonexistent-intent",
    ).as_(bot)
    factory = FakeBgFactory()
    error = ErrorEvent(
        update=Update(update_id=901, callback_query=callback).as_(bot),
        exception=UnknownIntent("intent is gone"),
    )
    # Must not raise: ErrorEvent has no `from_user`, which broke the earlier implementation.
    await on_stale_dialog(error, bg_factory=factory)

    assert factory.manager.started == [MainSG.menu]
    answered = [c for c in bot.calls if type(c).__name__ == "AnswerCallbackQuery"]
    assert answered and "outdated" in answered[-1].text
