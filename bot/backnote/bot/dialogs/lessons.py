from datetime import date, datetime
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Calendar,
    Cancel,
    CopyText,
    Group,
    Row,
    ScrollingGroup,
    Select,
    SwitchTo,
    Url,
)
from aiogram_dialog.widgets.text import Const, Format

from backnote.bot.dialogs.common import (
    BACK,
    CANCEL,
    DANGER,
    PRIMARY,
    SUCCESS,
    DynamicPreview,
    Field,
    can_delete,
    copy_start_data,
    data_id,
    deep_link,
    field_buttons,
    field_editor_window,
    notifier,
    settings,
    svc,
    uid,
)
from backnote.bot.dialogs.states import LessonCreateSG, LessonsSG, MaterialsSG, SummarySG, TasksSG
from backnote.db.models import LessonKind, SubjectKind
from backnote.formatting import (
    LESSON_KINDS,
    extract_url,
    fmt_date,
    h,
    lesson_button,
    lesson_heading,
    lesson_kind,
    progress_line,
    quote,
)

LESSON_FIELDS = {
    f.key: f
    for f in [
        Field("title", "📝 Title", "Send the new title.", optional=False),
        Field(
            "number",
            "🔢 Number",
            "Lesson number, e.g. 3.",
            "int",
            False,
            min_value=0,
            max_value=999,
        ),
        Field(
            "video_url", "▶️ Recording link", "YouTube or any other link to the recording.", "url"
        ),
        Field("description", "📄 Description", "Topics, reading list, remarks…", "longtext"),
    ]
}


def kind_items() -> list[dict]:
    return [{"id": k.value, "label": m.label} for k, m in LESSON_KINDS.items()]


# ------------------------------------------------------------------ list


async def list_getter(dialog_manager: DialogManager, **_):
    s = svc(dialog_manager)
    subject = await s.subjects.get(data_id(dialog_manager, "subject_id"))
    rows = await s.lessons.list_with_progress(subject.id, uid(dialog_manager))
    only_open = bool(dialog_manager.dialog_data.get("only_open"))
    done = sum(r.done for r in rows)
    visible = [r for r in rows if not (only_open and r.done)]
    lines = [f"🎓 <b>Lessons</b> · {h(subject.title)}"]
    if rows:
        lines.append(f"<code>{progress_line(done, len(rows))}</code>")
        lines.append("<i>✅ marks lessons you completed. Marks are personal.</i>")
        if only_open and not visible:
            lines.append("\n<blockquote>All done here </blockquote>")
    else:
        lines.append("\n<blockquote>No lessons yet. Add the first lecture!</blockquote>")
    return {
        "text": "\n".join(lines),
        "items": [{"id": r.lesson.id, "label": lesson_button(r.lesson, r.done)} for r in visible],
        "filter_label": "👁 Show all" if only_open else "⏳ Only unfinished",
        "has_lessons": bool(rows),
    }


async def on_lesson(_c: CallbackQuery, _w, manager: DialogManager, lesson_id: int) -> None:
    manager.dialog_data["lesson_id"] = lesson_id
    await manager.switch_to(LessonsSG.view)


async def toggle_filter(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    manager.dialog_data["only_open"] = not manager.dialog_data.get("only_open")


async def on_add(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await manager.start(LessonCreateSG.kind, data={"subject_id": data_id(manager, "subject_id")})


async def on_result(_start_data: Any, result: Any, manager: DialogManager) -> None:
    if isinstance(result, dict) and result.get("lesson_id"):
        manager.dialog_data["lesson_id"] = result["lesson_id"]
        await manager.switch_to(LessonsSG.view)


# ------------------------------------------------------------------ view


async def view_getter(dialog_manager: DialogManager, **_):
    s, user_id = svc(dialog_manager), uid(dialog_manager)
    lesson = await s.lessons.get(data_id(dialog_manager, "lesson_id"))
    if lesson is None:
        return {"text": "This lesson was deleted.", "missing": True, "preview_url": None}
    subject = await s.subjects.get(lesson.subject_id)
    completed = await s.progress.is_completed(lesson.id, user_id)
    materials = await s.materials.count_for_lesson(lesson.id)
    tasks = await s.tasks.count_for_lesson(lesson.id)
    note = await s.progress.get_note(lesson.id, user_id)
    prev_id, next_id = await s.lessons.neighbours(lesson)
    lines = [f"{lesson_kind(lesson.kind).emoji} <b>{h(lesson_heading(lesson))}</b>"]
    sub = f"📘 {h(subject.title)}"
    if lesson.held_on:
        sub += f" · {fmt_date(lesson.held_on)}"
    lines.append(sub)
    if lesson.description:
        lines.append(quote(lesson.description))
    if lesson.video_url:
        lines.append(f'\n▶️ <a href="{h(lesson.video_url)}">Recording</a>')
    if lesson.summary:
        source = "AI" if lesson.summary_source == "ai" else "written"
        summary_state = f"ready ({source})"
    else:
        summary_state = "—"
    lines.append(
        f"\n📎 Materials: <b>{materials}</b> · 🧠 Summary: <b>{summary_state}</b>"
        + (" · You have a note" if note else "")
    )
    lines.append("\n✓ <b>Completed</b>" if completed else "\n<i>Not completed yet</i>")
    return {
        "text": "\n".join(lines),
        "missing": False,
        "preview_url": lesson.video_url,
        "video_url": lesson.video_url,
        "toggle_label": "↩️ Mark as not completed" if completed else "✅ Mark as completed",
        "not_completed": not completed,
        "materials_label": f"📎 Materials ({materials})",
        "tasks_label": f"📋 Tasks ({tasks})",
        "summary_label": "🧠 Summary" + (" ✓" if lesson.summary else ""),
        "note_label": "🗒 My note" + (" ✓" if note else ""),
        "has_prev": prev_id is not None,
        "has_next": next_id is not None,
        "share_link": deep_link(dialog_manager, f"l{lesson.id}"),
    }


async def toggle_completed(callback: CallbackQuery, _b, manager: DialogManager) -> None:
    done = await svc(manager).progress.toggle_lesson(data_id(manager, "lesson_id"), uid(manager))
    await callback.answer("Marked as completed " if done else "Mark removed")


async def go_neighbour(_c: CallbackQuery, button: Button, manager: DialogManager) -> None:
    lesson = await svc(manager).lessons.get(data_id(manager, "lesson_id"))
    prev_id, next_id = await svc(manager).lessons.neighbours(lesson)
    target = prev_id if button.widget_id == "prev" else next_id
    if target:
        manager.dialog_data["lesson_id"] = target


async def open_summary(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await manager.start(SummarySG.main, data={"lesson_id": data_id(manager, "lesson_id")})


async def open_materials(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await manager.start(
        MaterialsSG.list,
        data={
            "subject_id": data_id(manager, "subject_id"),
            "lesson_id": data_id(manager, "lesson_id"),
        },
    )


async def open_tasks(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await manager.start(
        TasksSG.list,
        data={
            "subject_id": data_id(manager, "subject_id"),
            "lesson_id": data_id(manager, "lesson_id"),
        },
    )


# ------------------------------------------------------------------ note


async def note_getter(dialog_manager: DialogManager, **_):
    note = await svc(dialog_manager).progress.get_note(
        data_id(dialog_manager, "lesson_id"), uid(dialog_manager)
    )
    current = quote(note, expandable=False) if note else "<i>No note yet.</i>"
    return {
        "text": (
            "<b>My note</b> — private, only you can see it.\n\n"
            f"{current}\n\n<i>Send text to replace the note.</i>"
        ),
        "has_note": bool(note),
    }


async def on_note(message: Message, _w, manager: DialogManager) -> None:
    text = (message.text or "").strip()
    if len(text) > 4000:
        await message.answer("⚠️ Keep the note under 4000 characters.")
        return
    await svc(manager).progress.set_note(data_id(manager, "lesson_id"), uid(manager), text)
    await manager.switch_to(LessonsSG.view)


async def delete_note(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await svc(manager).progress.set_note(data_id(manager, "lesson_id"), uid(manager), None)


# ------------------------------------------------------------------ edit


async def edit_getter(dialog_manager: DialogManager, **_):
    lesson = await svc(dialog_manager).lessons.get(data_id(dialog_manager, "lesson_id"))
    return {
        "text": f"<b>Edit</b> · {h(lesson_heading(lesson))}",
        "can_delete": can_delete(dialog_manager, lesson.created_by),
    }


async def load_field(manager: DialogManager, key: str):
    lesson = await svc(manager).lessons.get(data_id(manager, "lesson_id"))
    return getattr(lesson, key)


async def save_field(manager: DialogManager, key: str, value) -> None:
    await svc(manager).lessons.update(data_id(manager, "lesson_id"), **{key: value})


async def kind_getter(dialog_manager: DialogManager, **_):
    return {"kinds": kind_items()}


async def on_edit_kind(_c: CallbackQuery, _w, manager: DialogManager, kind: str) -> None:
    await svc(manager).lessons.update(data_id(manager, "lesson_id"), kind=LessonKind(kind))
    await manager.switch_to(LessonsSG.edit)


async def date_getter(dialog_manager: DialogManager, **_):
    lesson = await svc(dialog_manager).lessons.get(data_id(dialog_manager, "lesson_id"))
    current = fmt_date(lesson.held_on) if lesson.held_on else "not set"
    return {"current": current}


async def on_date(_c: CallbackQuery, _w, manager: DialogManager, selected: date) -> None:
    await svc(manager).lessons.update(data_id(manager, "lesson_id"), held_on=selected)
    await manager.switch_to(LessonsSG.edit)


async def on_today(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    today = datetime.now(settings(manager).tz).date()
    await on_date(_c, _b, manager, today)


async def on_clear_date(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await svc(manager).lessons.update(data_id(manager, "lesson_id"), held_on=None)
    await manager.switch_to(LessonsSG.edit)


async def delete_getter(dialog_manager: DialogManager, **_):
    lesson = await svc(dialog_manager).lessons.get(data_id(dialog_manager, "lesson_id"))
    return {
        "text": (
            f"Delete <b>{h(lesson_heading(lesson))}</b>?\n\n<blockquote>Its materials, "
            "summary, notes and everyone's progress will be removed.</blockquote>"
        )
    }


async def on_delete(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    lesson = await svc(manager).lessons.get(data_id(manager, "lesson_id"))
    if lesson and can_delete(manager, lesson.created_by):
        await svc(manager).lessons.delete(lesson.id)
    manager.dialog_data.pop("lesson_id", None)
    await manager.switch_to(LessonsSG.list)


def lessons_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{text}"),
            ScrollingGroup(
                Select(
                    Format("{item[label]}"),
                    id="lesson",
                    item_id_getter=lambda x: x["id"],
                    items="items",
                    type_factory=int,
                    on_click=on_lesson,
                ),
                id="lessons_scroll",
                width=1,
                height=8,
                hide_on_single_page=True,
            ),
            Row(
                Button(Const("➕ Add lesson"), id="add", on_click=on_add, style=PRIMARY),
                Button(
                    Format("{filter_label}"),
                    id="filter",
                    on_click=toggle_filter,
                    when="has_lessons",
                ),
            ),
            Cancel(BACK),
            state=LessonsSG.list,
            getter=list_getter,
        ),
        Window(
            Format("{text}"),
            DynamicPreview(),
            Group(
                Button(
                    Format("{toggle_label}"),
                    id="toggle",
                    on_click=toggle_completed,
                    style=SUCCESS,
                    when="not_completed",
                ),
                Button(
                    Format("{toggle_label}"),
                    id="untoggle",
                    on_click=toggle_completed,
                    when=lambda d, *_: not d["not_completed"],
                ),
                Row(
                    Url(Const("▶️ Watch"), Format("{video_url}"), when="video_url"),
                    Button(Format("{summary_label}"), id="summary", on_click=open_summary),
                ),
                Row(
                    Button(Format("{materials_label}"), id="materials", on_click=open_materials),
                    SwitchTo(Format("{note_label}"), id="note", state=LessonsSG.note),
                ),
                Row(Button(Format("{tasks_label}"), id="tasks", on_click=open_tasks)),
                Row(
                    Button(Const("⬅️ Prev"), id="prev", on_click=go_neighbour, when="has_prev"),
                    Button(Const("Next ➡️"), id="next", on_click=go_neighbour, when="has_next"),
                ),
                Row(
                    CopyText(Const("🔗 Copy link"), Format("{share_link}")),
                    SwitchTo(Const("✏️ Edit"), id="edit", state=LessonsSG.edit),
                ),
                when=lambda d, *_: not d["missing"],
            ),
            SwitchTo(Const("📋 All lessons"), id="back", state=LessonsSG.list),
            state=LessonsSG.view,
            getter=view_getter,
        ),
        Window(
            Format("{text}"),
            MessageInput(on_note, content_types=["text"]),
            Button(Const("🗑 Delete note"), id="del_note", on_click=delete_note, when="has_note"),
            SwitchTo(BACK, id="back", state=LessonsSG.view),
            state=LessonsSG.note,
            getter=note_getter,
        ),
        Window(
            Format("{text}"),
            field_buttons(LESSON_FIELDS, LessonsSG.edit_field),
            Row(
                SwitchTo(Const("🏷 Type"), id="kind", state=LessonsSG.edit_kind),
                SwitchTo(Const("📅 Date"), id="date", state=LessonsSG.edit_date),
            ),
            SwitchTo(
                Const("🗑 Delete lesson"),
                id="delete",
                state=LessonsSG.delete,
                when="can_delete",
                style=DANGER,
            ),
            SwitchTo(BACK, id="back", state=LessonsSG.view),
            state=LessonsSG.edit,
            getter=edit_getter,
        ),
        field_editor_window(
            LessonsSG.edit_field, LessonsSG.edit, LESSON_FIELDS, load_field, save_field
        ),
        Window(
            Const("🏷 <b>Lesson type</b>"),
            Group(
                Select(
                    Format("{item[label]}"),
                    id="kind",
                    item_id_getter=lambda x: x["id"],
                    items="kinds",
                    on_click=on_edit_kind,
                ),
                width=2,
            ),
            SwitchTo(BACK, id="back", state=LessonsSG.edit),
            state=LessonsSG.edit_kind,
            getter=kind_getter,
        ),
        Window(
            Format("📅 <b>When did it take place?</b>\n\nCurrent: <b>{current}</b>"),
            Calendar(id="held_on", on_click=on_date),
            Row(
                Button(Const("📍 Today"), id="today", on_click=on_today),
                Button(Const("🧹 Clear"), id="clear", on_click=on_clear_date),
            ),
            SwitchTo(BACK, id="back", state=LessonsSG.edit),
            state=LessonsSG.edit_date,
            getter=date_getter,
        ),
        Window(
            Format("{text}"),
            Row(
                Button(Const("🗑 Yes, delete"), id="confirm", on_click=on_delete, style=DANGER),
                SwitchTo(CANCEL, id="cancel", state=LessonsSG.edit),
            ),
            state=LessonsSG.delete,
            getter=delete_getter,
        ),
        on_start=copy_start_data,
        on_process_result=on_result,
    )


# ------------------------------------------------------------------ create wizard


async def create_kind_getter(dialog_manager: DialogManager, **_):
    subject = await svc(dialog_manager).subjects.get(data_id(dialog_manager, "subject_id"))
    kinds = kind_items()
    if subject.kind == SubjectKind.COURSE:
        # Online courses are mostly videos and readings.
        order = [LessonKind.VIDEO, LessonKind.READING, LessonKind.LECTURE, LessonKind.PRACTICE]
        kinds.sort(key=lambda k: order.index(k["id"]) if k["id"] in order else len(order))
    return {"subject": h(subject.title), "kinds": kinds}


async def create_kind(_c: CallbackQuery, _w, manager: DialogManager, kind: str) -> None:
    manager.dialog_data["kind"] = kind
    manager.dialog_data["number"] = await svc(manager).lessons.next_number(
        data_id(manager, "subject_id"), LessonKind(kind)
    )
    await manager.switch_to(LessonCreateSG.number)


async def create_number_getter(dialog_manager: DialogManager, **_):
    d = dialog_manager.dialog_data
    meta = lesson_kind(d["kind"])
    return {
        "label": meta.label.lower(),
        "number": d["number"],
        "use_label": f"{meta.label} {d['number']}",
    }


async def create_number(message: Message, _w, manager: DialogManager) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) > 999:
        await message.answer("⚠️ Send a number from 0 to 999.")
        return
    manager.dialog_data["number"] = int(raw)
    await manager.switch_to(LessonCreateSG.title)


async def create_title_getter(dialog_manager: DialogManager, **_):
    d = dialog_manager.dialog_data
    return {"heading": f"{lesson_kind(d['kind']).label} {d['number']}"}


async def create_title(message: Message, _w, manager: DialogManager) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 256:
        await message.answer("⚠️ Send a title up to 256 characters.")
        return
    manager.dialog_data["title"] = title
    await manager.switch_to(LessonCreateSG.video)


async def _create_lesson(manager: DialogManager, video_url: str | None) -> None:
    d = manager.dialog_data
    s = svc(manager)
    lesson = await s.lessons.create(
        subject_id=data_id(manager, "subject_id"),
        number=d["number"],
        kind=LessonKind(d["kind"]),
        title=d["title"],
        video_url=video_url,
        created_by=uid(manager),
    )
    subject = await s.subjects.get(lesson.subject_id)
    author = await s.users.get(uid(manager))
    notifier(manager).new_lesson(lesson, subject, author)
    await manager.done({"lesson_id": lesson.id})


async def create_video(message: Message, _w, manager: DialogManager) -> None:
    url = extract_url(message)
    if not url:
        await message.answer("⚠️ I couldn't find a link in that message. Try again or skip.")
        return
    await _create_lesson(manager, url)


async def skip_video(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await _create_lesson(manager, None)


def lesson_create_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("🎓 <b>New lesson</b> · {subject}\n\nWhat kind of session is it?"),
            Group(
                Select(
                    Format("{item[label]}"),
                    id="kind",
                    item_id_getter=lambda x: x["id"],
                    items="kinds",
                    on_click=create_kind,
                ),
                width=2,
            ),
            Cancel(CANCEL),
            state=LessonCreateSG.kind,
            getter=create_kind_getter,
        ),
        Window(
            Format(
                "🔢 <b>Number</b>\n\nThe next {label} number is <b>{number}</b>.\n"
                "<i>Tap to confirm or send another number.</i>"
            ),
            SwitchTo(Format("{use_label}"), id="use", state=LessonCreateSG.title, style=PRIMARY),
            MessageInput(create_number, content_types=["text"]),
            SwitchTo(BACK, id="back", state=LessonCreateSG.kind),
            state=LessonCreateSG.number,
            getter=create_number_getter,
        ),
        Window(
            Format("📝 <b>{heading}</b>\n\nSend the topic / title of the session."),
            MessageInput(create_title, content_types=["text"]),
            SwitchTo(BACK, id="back", state=LessonCreateSG.number),
            Cancel(CANCEL),
            state=LessonCreateSG.title,
            getter=create_title_getter,
        ),
        Window(
            Const(
                "▶️ <b>Recording</b>\n\nSend the YouTube link (or any link to the recording).\n"
                "<i>Forwarding a message that contains the link works too.</i>"
            ),
            MessageInput(create_video),
            Button(Const("⏭ No recording — create"), id="skip", on_click=skip_video),
            SwitchTo(BACK, id="back", state=LessonCreateSG.title),
            state=LessonCreateSG.video,
        ),
        on_start=copy_start_data,
    )
