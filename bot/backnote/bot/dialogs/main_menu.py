from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Row, Start, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from backnote.bot.dialogs.common import BACK, PRIMARY, settings, svc, uid
from backnote.bot.dialogs.states import AdminSG, LessonsSG, MainSG, SearchSG, SubjectsSG
from backnote.bot.rich import send_markdown
from backnote.db.models import SubjectKind
from backnote.formatting import SUBJECT_KINDS, h, lesson_code, percent, progress_bar


async def menu_getter(dialog_manager: DialogManager, **_):
    s, user_id = svc(dialog_manager), uid(dialog_manager)
    subjects = await s.subjects.count(SubjectKind.SUBJECT)
    courses = await s.subjects.count(SubjectKind.COURSE)
    lessons = await s.lessons.count()
    done = await s.progress.completed_count(user_id)
    cont = await s.progress.continue_lesson(user_id)

    lines = [
        "📚 <b>Backnote</b>",
        f"<blockquote>Your study base\n"
        f"• {subjects} subjects · {courses} courses · {lessons} lessons\n"
        f"• Completed: {done}</blockquote>",
    ]
    if cont:
        lesson, subject = cont
        lines.append(f"▶️ Next in <b>{h(subject.title)}</b>:\n{h(lesson.title)}")

    return {
        "text": "\n".join(lines),
        "is_admin": user_id == settings(dialog_manager).admin_id,
        "has_continue": cont is not None,
        "continue_label": f"▶ Continue: {lesson_code(cont[0])}" if cont else "",
    }


async def on_continue(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    cont = await svc(manager).progress.continue_lesson(uid(manager))
    if cont:
        lesson, subject = cont
        await manager.start(LessonsSG.view, data={"subject_id": subject.id, "lesson_id": lesson.id})


async def progress_getter(dialog_manager: DialogManager, **_):
    rows = await svc(dialog_manager).progress.overview(uid(dialog_manager))
    if not rows:
        return {"text": "📊 <b>Your progress</b>\n\n<blockquote>No lessons yet.</blockquote>"}
    total = sum(r.total for r in rows)
    done = sum(r.done for r in rows)
    blocks = [
        f"{SUBJECT_KINDS[r.subject.kind].emoji} <b>{h(r.subject.title)}</b>\n"
        f"<code>{progress_bar(r.done, r.total)}</code> {r.done}/{r.total} · "
        f"{percent(r.done, r.total)}%"
        for r in rows
    ]
    text = (
        "📊 <b>Your progress</b>\n"
        f"<blockquote>Overall: <b>{done}/{total}</b> lessons · {percent(done, total)}%\n"
        f"<code>{progress_bar(done, total, 16)}</code></blockquote>\n\n" + "\n\n".join(blocks)
    )
    return {"text": text}


async def settings_getter(dialog_manager: DialogManager, **_):
    user = await svc(dialog_manager).users.get(uid(dialog_manager))
    return {
        "new_label": f"New lessons: {'on' if user.notify_new_content else 'off'}",
    }


async def toggle_new_content(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    user = await svc(manager).users.get(uid(manager))
    await svc(manager).users.update_settings(
        uid(manager), notify_new_content=not user.notify_new_content
    )


# Telegram keeps line breaks from the source, so each paragraph is a single line.
HELP = "\n\n".join(
    [
        "❔ <b>How Backnote works</b>",
        "<b>Subjects</b> are university courses of your programme, tagged with study year "
        "and term (3 terms a year).\n<b>Courses</b> are online courses and extra tracks: AI, "
        "agents, Coursera, YouTube playlists.",
        "Inside each one:\n"
        "• <b>Lessons</b> — lectures with recording link, summary and your note.\n"
        "• <b>Materials</b> — syllabus, slides, books, useful links.",
        "<blockquote>🔒 <b>Personal:</b> completion marks and notes — only you see them.\n"
        "👥 <b>Shared:</b> subjects, lessons, materials and summaries.</blockquote>",
        "🧠 <b>Summaries</b> are sent as Telegram rich messages, so full Markdown works: "
        "headings, lists, tables, formulas, code blocks and collapsible answers.\n"
        "<i>Tap the button below to see a live example.</i>",
        "<b>Commands</b>\n/start — main menu\n/id — your Telegram ID",
    ]
)

MARKDOWN_DEMO = r"""# Lecture 3 · Transformers

*Deep Learning* — example summary

## Key ideas
- **Self-attention** lets every token look at every other token
- ==Positional encoding== adds order information
- Training is parallel, unlike RNNs

## Formula
$$\mathrm{Attention}(Q, K, V) = \mathrm{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

## Comparison
| Model | Parallel | Long context |
|:--|:--:|:--:|
| RNN | no | weak |
| Transformer | yes | strong |

## Code
```python
scores = q @ k.transpose(-2, -1) / d_k ** 0.5
weights = scores.softmax(dim=-1)
```

## Self-check
- [x] What problem does attention solve?
- [ ] Why divide by $\sqrt{d_k}$?

<details><summary>Answer</summary>Large dot products saturate softmax.</details>

---
_This is how summaries look. Write yours in the same Markdown._"""


async def on_markdown_demo(callback: CallbackQuery, _b, manager: DialogManager) -> None:
    await send_markdown(callback.bot, callback.message.chat.id, MARKDOWN_DEMO)
    await callback.answer()


def main_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{text}"),
            Button(
                Format("{continue_label}"),
                id="continue",
                on_click=on_continue,
                when="has_continue",
                style=PRIMARY,
            ),
            Row(
                Start(
                    Const("📘 Subjects"),
                    id="subjects",
                    state=SubjectsSG.list,
                    data={"kind": SubjectKind.SUBJECT.value},
                ),
                Start(
                    Const("🎯 Courses"),
                    id="courses",
                    state=SubjectsSG.list,
                    data={"kind": SubjectKind.COURSE.value},
                ),
            ),
            Row(
                Start(Const("🔎 Search"), id="search", state=SearchSG.query),
                SwitchTo(Const("📊 Progress"), id="progress", state=MainSG.progress),
            ),
            Row(
                SwitchTo(Const("⚙️ Settings"), id="settings", state=MainSG.settings),
                SwitchTo(Const("❔ Help"), id="help", state=MainSG.help),
                Start(Const("🛡 Admin"), id="admin", state=AdminSG.menu, when="is_admin"),
            ),
            state=MainSG.menu,
            getter=menu_getter,
        ),
        Window(
            Format("{text}"),
            SwitchTo(BACK, id="back", state=MainSG.menu),
            state=MainSG.progress,
            getter=progress_getter,
        ),
        Window(
            Const(
                "<b>Settings</b>\n\n"
                "<blockquote>Get a message when someone adds a new lesson.</blockquote>"
            ),
            Button(Format("{new_label}"), id="t_new", on_click=toggle_new_content),
            SwitchTo(BACK, id="back", state=MainSG.menu),
            state=MainSG.settings,
            getter=settings_getter,
        ),
        Window(
            Const(HELP),
            Button(Const("Show Markdown example"), id="md_demo", on_click=on_markdown_demo),
            SwitchTo(BACK, id="back", state=MainSG.menu),
            state=MainSG.help,
        ),
    )
