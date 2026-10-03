"""Tasks attached to a subject or a lesson: .py / .md / .html files (or plain text as Markdown).

Mirrors materials.py. The site renders them (HTML pages, Markdown, runnable Python);
in the bot you can add, read and download them.
"""

from pathlib import PurePosixPath

from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
    Url,
)
from aiogram_dialog.widgets.text import Const, Format

from backnote.bot.dialogs.common import (
    BACK,
    DANGER,
    PRIMARY,
    can_delete,
    copy_start_data,
    data_id,
    resend,
    settings,
    svc,
    uid,
)
from backnote.bot.dialogs.states import TasksSG
from backnote.formatting import fmt_datetime, h, lesson_heading

MAX_BYTES = 1_000_000
KIND_BY_EXT = {
    ".py": "python",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "markdown",
    ".html": "html",
    ".htm": "html",
}
EMOJI = {"python": "🐍", "markdown": "📝", "html": "🧩"}


def _target(m: DialogManager) -> dict:
    return {"subject_id": data_id(m, "subject_id"), "lesson_id": data_id(m, "lesson_id")}


async def _context_title(m: DialogManager) -> str:
    s = svc(m)
    if (lesson_id := data_id(m, "lesson_id")) is not None:
        return h(lesson_heading(await s.lessons.get(lesson_id)))
    return h((await s.subjects.get(data_id(m, "subject_id"))).title)


async def list_getter(dialog_manager: DialogManager, **_):
    tasks = await svc(dialog_manager).tasks.list_for(**_target(dialog_manager))
    hint = (
        "<i>Tap a task to read it or download the file.</i>"
        if tasks
        else "<blockquote>No tasks yet. Send a .py, .md or .html file to add one.</blockquote>"
    )
    return {
        "text": f"📋 <b>Tasks</b> · {await _context_title(dialog_manager)}\n\n{hint}",
        "items": [{"id": t.id, "label": f"{EMOJI.get(t.kind, '')} {t.title}"} for t in tasks],
    }


async def on_task(_c: CallbackQuery, _w, manager: DialogManager, item: int) -> None:
    manager.dialog_data["task_id"] = item
    await manager.switch_to(TasksSG.view)


async def view_getter(dialog_manager: DialogManager, **_):
    task = await svc(dialog_manager).tasks.get(data_id(dialog_manager, "task_id"))
    if task is None:
        return {"text": "This task was deleted.", "missing": True}
    cfg = settings(dialog_manager)
    author = await svc(dialog_manager).users.get(task.created_by) if task.created_by else None
    added = fmt_datetime(task.created_at, cfg.tz)
    lines = [
        f"{EMOJI.get(task.kind, '')} <b>{h(task.title)}</b>",
        f"<i>{task.kind} · added {added}" + (f" by {h(author.display_name)}" if author else "") + "</i>",
    ]
    if task.kind != "html":
        preview = task.content[:600] + ("…" if len(task.content) > 600 else "")
        lines.append(f"\n<pre>{h(preview)}</pre>")
    else:
        lines.append("\n<blockquote>HTML tasks are interactive — open them on the site.</blockquote>")
    web = getattr(cfg, "web_url", None)
    return {
        "text": "\n".join(lines),
        "missing": False,
        "web_url": f"{web.rstrip('/')}/tasks/{task.id}" if web else None,
        "can_delete": can_delete(dialog_manager, task.created_by),
    }


async def on_send_file(callback: CallbackQuery, _b, manager: DialogManager) -> None:
    task = await svc(manager).tasks.get(data_id(manager, "task_id"))
    if task is None:
        return
    name = task.file_name or f"{task.title}.{ {'python': 'py', 'html': 'html'}.get(task.kind, 'md') }"
    await callback.message.answer_document(
        BufferedInputFile(task.content.encode(), filename=name), caption=h(task.title)
    )
    resend(manager)


async def on_add_input(message: Message, _w, manager: DialogManager) -> None:
    if message.document:
        doc = message.document
        ext = PurePosixPath(doc.file_name or "").suffix.lower()
        kind = KIND_BY_EXT.get(ext)
        if kind is None:
            await message.answer("⚠️ Supported files: .py, .md, .html")
            return
        if (doc.file_size or 0) > MAX_BYTES:
            await message.answer("⚠️ The file is too large (up to 1 MB).")
            return
        buffer = await message.bot.download(doc)
        try:
            content = buffer.read().decode("utf-8")
        except UnicodeDecodeError:
            await message.answer("⚠️ The file must be UTF-8 text.")
            return
        title = (message.caption or "").strip().split("\n")[0][:200] or PurePosixPath(
            doc.file_name
        ).stem
        file_name = doc.file_name
    elif message.text and not message.text.startswith("/"):
        content, kind, file_name = message.text, "markdown", None
        title = message.text.strip().split("\n")[0].lstrip("# ")[:200] or "Task"
    else:
        await message.answer("⚠️ Send a .py / .md / .html file or the task text.")
        return
    task = await svc(manager).tasks.create(
        **_target(manager),
        kind=kind,
        title=title,
        content=content,
        file_name=file_name,
        created_by=uid(manager),
    )
    manager.dialog_data["task_id"] = task.id
    manager.dialog_data["added"] = manager.dialog_data.get("added", 0) + 1


async def add_getter(dialog_manager: DialogManager, **_):
    added = dialog_manager.dialog_data.get("added", 0)
    status = f"\n\nAdded {added} task(s). Send more or finish." if added else ""
    return {
        "text": (
            "📋 <b>Add tasks</b>\n\nSend a <code>.py</code>, <code>.md</code> or <code>.html</code> "
            "file (the caption becomes the title), or just type the task text." + status
        )
    }


async def finish_adding(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    manager.dialog_data.pop("added", None)
    await manager.switch_to(TasksSG.list)


async def on_delete(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    task = await svc(manager).tasks.get(data_id(manager, "task_id"))
    if task and can_delete(manager, task.created_by):
        await svc(manager).tasks.delete(task.id)
    await manager.switch_to(TasksSG.list)


def tasks_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{text}"),
            ScrollingGroup(
                Select(
                    Format("{item[label]}"),
                    id="task",
                    item_id_getter=lambda x: x["id"],
                    items="items",
                    type_factory=int,
                    on_click=on_task,
                ),
                id="tasks_scroll",
                width=1,
                height=8,
                hide_on_single_page=True,
            ),
            SwitchTo(Const("➕ Add"), id="add", state=TasksSG.add, style=PRIMARY),
            Cancel(BACK),
            state=TasksSG.list,
            getter=list_getter,
        ),
        Window(
            Format("{text}"),
            MessageInput(on_add_input),
            Button(Const("✅ Done"), id="done", on_click=finish_adding),
            state=TasksSG.add,
            getter=add_getter,
        ),
        Window(
            Format("{text}"),
            Row(
                Button(Const("📥 Get file"), id="file", on_click=on_send_file, when="not missing"),
                Url(Const("🌐 Open on site"), Format("{web_url}"), when="web_url"),
            ),
            Button(Const("🗑 Delete"), id="delete", on_click=on_delete, style=DANGER, when="can_delete"),
            SwitchTo(BACK, id="back", state=TasksSG.list),
            state=TasksSG.view,
            getter=view_getter,
        ),
        on_start=copy_start_data,
    )
