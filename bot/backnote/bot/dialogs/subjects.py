from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
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
    Field,
    can_delete,
    copy_start_data,
    data_id,
    field_buttons,
    field_editor_window,
    svc,
    uid,
)
from backnote.bot.dialogs.states import (
    LessonsSG,
    MaterialsSG,
    SubjectCreateSG,
    SubjectsSG,
    TasksSG,
)
from backnote.db.models import SubjectKind
from backnote.formatting import (
    SUBJECT_KINDS,
    h,
    normalize_url,
    progress_line,
    quote,
    subject_button,
    term_label,
)

YEARS = [1, 2, 3, 4]
TERMS = [1, 2, 3]

SUBJECT_FIELDS = {
    f.key: f
    for f in [
        Field("title", "📝 Title", "Send the new title.", optional=False),
        Field("code", "🏷 Code", "Course code from the syllabus, e.g. ECON 101.", max_len=32),
        Field("instructor", "👤 Instructor", "Who teaches it?"),
        Field("description", "📄 Description", "What is it about? Grading, rules…", "longtext"),
        Field("ects", "🏅 ECTS", "Number of ECTS credits.", "int", min_value=0, max_value=60),
        Field("url", "🔗 Link", "Course page, LMS or syllabus link.", "url"),
    ]
}
COURSE_FIELDS = {
    **SUBJECT_FIELDS,
    "provider": Field("provider", "🏫 Provider", "Coursera, edX, Udemy, company name…"),
}


def kind_of(m: DialogManager) -> SubjectKind:
    return SubjectKind(m.dialog_data.get("kind", SubjectKind.SUBJECT))


def fields_for(m: DialogManager) -> dict[str, Field]:
    return COURSE_FIELDS if kind_of(m) == SubjectKind.COURSE else SUBJECT_FIELDS


# ------------------------------------------------------------------ list


async def list_getter(dialog_manager: DialogManager, **_):
    kind = kind_of(dialog_manager)
    archived = bool(dialog_manager.dialog_data.get("archived"))
    rows = await svc(dialog_manager).subjects.list_with_progress(
        kind, uid(dialog_manager), archived=archived
    )
    meta = SUBJECT_KINDS[kind]
    intro = (
        "University subjects of your programme, newest term first."
        if kind == SubjectKind.SUBJECT
        else "Online courses and extra learning tracks — Coursera, edX, bootcamps…"
    )
    title = f"{meta.emoji} <b>{'Archived ' if archived else ''}{meta.short}</b>"
    if rows:
        body = f"<i>{intro} Buttons show your progress: done/total lessons.</i>"
    else:
        body = (
            "<blockquote>The archive is empty.</blockquote>"
            if archived
            else f"<i>{intro}</i>\n\n<blockquote>Nothing here yet — add the first one!</blockquote>"
        )
    return {
        "text": f"{title}\n\n{body}",
        "items": [
            {"id": r.subject.id, "label": subject_button(r.subject, r.total, r.done)} for r in rows
        ],
        "add_label": f"➕ Add {meta.label.lower()}",
        "archive_label": "📂 Show active" if archived else "🗄 Archive",
    }


async def on_subject(_c: CallbackQuery, _w, manager: DialogManager, subject_id: int) -> None:
    manager.dialog_data["subject_id"] = subject_id
    await manager.switch_to(SubjectsSG.view)


async def on_add(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await manager.start(SubjectCreateSG.title, data={"kind": kind_of(manager).value})


async def toggle_archived(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    manager.dialog_data["archived"] = not manager.dialog_data.get("archived")


async def on_result(_start_data: Any, result: Any, manager: DialogManager) -> None:
    if isinstance(result, dict) and result.get("subject_id"):
        manager.dialog_data["subject_id"] = result["subject_id"]
        await manager.switch_to(SubjectsSG.view)


# ------------------------------------------------------------------ view


async def view_getter(dialog_manager: DialogManager, **_):
    s, user_id = svc(dialog_manager), uid(dialog_manager)
    subject = await s.subjects.get(data_id(dialog_manager, "subject_id"))
    if subject is None:
        return {"text": "This item was deleted.", "missing": True}
    lessons = await s.lessons.list_with_progress(subject.id, user_id)
    done = sum(r.done for r in lessons)
    materials = len(await s.materials.list_for(subject_id=subject.id))
    tasks = len(await s.tasks.list_for(subject_id=subject.id))

    head = f"{SUBJECT_KINDS[subject.kind].emoji} <b>{h(subject.title)}</b>"
    if subject.code:
        head += f"  <code>{h(subject.code)}</code>"
    facts = [
        f"👤 {h(subject.instructor)}" if subject.instructor else None,
        f"🏫 {h(subject.provider)}" if subject.provider else None,
        f"🗓 {term_label(subject.year, subject.term)}"
        if term_label(subject.year, subject.term)
        else None,
        f"🏅 {subject.ects} ECTS" if subject.ects is not None else None,
    ]
    lines = [head]
    if any(facts):
        lines.append(" · ".join(f for f in facts if f))
    if subject.description:
        lines.append(quote(subject.description))
    lines.append(f"\n📊 <b>Your progress</b>\n<code>{progress_line(done, len(lessons))}</code>")
    if subject.is_archived:
        lines.append("\n🗄 <i>This item is archived.</i>")
    return {
        "text": "\n".join(lines),
        "missing": False,
        "lessons_label": f"🎓 Lessons ({len(lessons)})",
        "materials_label": f"📎 Materials ({materials})",
        "tasks_label": f"📋 Tasks ({tasks})",
        "url": subject.url,
        "is_course": subject.kind == SubjectKind.COURSE,
    }


def _starter(state, key: str):
    async def handler(_c: CallbackQuery, _b, manager: DialogManager) -> None:
        await manager.start(state, data={"subject_id": data_id(manager, "subject_id")})

    handler.__name__ = f"open_{key}"
    return handler


# ------------------------------------------------------------------ edit


async def edit_getter(dialog_manager: DialogManager, **_):
    subject = await svc(dialog_manager).subjects.get(data_id(dialog_manager, "subject_id"))
    kind = kind_of(dialog_manager)
    return {
        "text": f"✏️ <b>Edit</b> · {h(subject.title)}\n\n<i>What do you want to change?</i>",
        "is_course": kind == SubjectKind.COURSE,
        "is_subject": kind == SubjectKind.SUBJECT,
        "archive_label": "📂 Unarchive" if subject.is_archived else "🗄 Archive",
        "can_delete": can_delete(dialog_manager, subject.created_by),
    }


async def load_field(manager: DialogManager, key: str):
    subject = await svc(manager).subjects.get(data_id(manager, "subject_id"))
    return getattr(subject, key)


async def save_field(manager: DialogManager, key: str, value) -> None:
    await svc(manager).subjects.update(data_id(manager, "subject_id"), **{key: value})


async def toggle_archive(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    subject_id = data_id(manager, "subject_id")
    subject = await svc(manager).subjects.get(subject_id)
    await svc(manager).subjects.update(subject_id, is_archived=not subject.is_archived)
    await manager.switch_to(SubjectsSG.view)


async def term_getter(dialog_manager: DialogManager, **_):
    subject = await svc(dialog_manager).subjects.get(data_id(dialog_manager, "subject_id"))
    return {
        "current": term_label(subject.year, subject.term) or "not set",
        "years": [{"n": y, "label": f"{'• ' if subject.year == y else ''}Year {y}"} for y in YEARS],
        "terms": [{"n": t, "label": f"{'• ' if subject.term == t else ''}T{t}"} for t in TERMS],
    }


async def on_year(_c: CallbackQuery, _w, manager: DialogManager, year: int) -> None:
    await svc(manager).subjects.update(data_id(manager, "subject_id"), year=year)


async def on_term(_c: CallbackQuery, _w, manager: DialogManager, term: int) -> None:
    await svc(manager).subjects.update(data_id(manager, "subject_id"), term=term)


async def clear_term(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await svc(manager).subjects.update(data_id(manager, "subject_id"), year=None, term=None)


async def delete_getter(dialog_manager: DialogManager, **_):
    s = svc(dialog_manager)
    subject = await s.subjects.get(data_id(dialog_manager, "subject_id"))
    lessons = await s.lessons.list_with_progress(subject.id, uid(dialog_manager))
    return {
        "text": (
            f"🗑 Delete <b>{h(subject.title)}</b>?\n\n"
            f"<blockquote>This removes {len(lessons)} lessons with all their materials, "
            "summaries and everyone's progress. It cannot be undone.\n"
            "Tip: use 🗄 Archive to just hide it.</blockquote>"
        )
    }


async def on_delete(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    subject = await svc(manager).subjects.get(data_id(manager, "subject_id"))
    if subject and can_delete(manager, subject.created_by):
        await svc(manager).subjects.delete(subject.id)
    manager.dialog_data.pop("subject_id", None)
    await manager.switch_to(SubjectsSG.list)


def _year_term_selects(on_year_click, on_term_click) -> list:
    return [
        Group(
            Select(
                Format("{item[label]}"),
                id="year",
                item_id_getter=lambda x: x["n"],
                items="years",
                type_factory=int,
                on_click=on_year_click,
            ),
            width=4,
        ),
        Group(
            Select(
                Format("{item[label]}"),
                id="term",
                item_id_getter=lambda x: x["n"],
                items="terms",
                type_factory=int,
                on_click=on_term_click,
            ),
            width=3,
        ),
    ]


def subjects_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{text}"),
            ScrollingGroup(
                Select(
                    Format("{item[label]}"),
                    id="subject",
                    item_id_getter=lambda x: x["id"],
                    items="items",
                    type_factory=int,
                    on_click=on_subject,
                ),
                id="subjects_scroll",
                width=1,
                height=8,
                hide_on_single_page=True,
            ),
            Row(
                Button(Format("{add_label}"), id="add", on_click=on_add, style=PRIMARY),
                Button(Format("{archive_label}"), id="archived", on_click=toggle_archived),
            ),
            Cancel(BACK),
            state=SubjectsSG.list,
            getter=list_getter,
        ),
        Window(
            Format("{text}"),
            Group(
                Button(
                    Format("{lessons_label}"),
                    id="lessons",
                    on_click=_starter(LessonsSG.list, "lessons"),
                    style=PRIMARY,
                ),
                Button(
                    Format("{materials_label}"),
                    id="materials",
                    on_click=_starter(MaterialsSG.list, "materials"),
                ),
                Button(
                    Format("{tasks_label}"),
                    id="tasks",
                    on_click=_starter(TasksSG.list, "tasks"),
                ),
                Url(Const("🔗 Open course page"), Format("{url}"), when="url"),
                SwitchTo(Const("✏️ Edit"), id="edit", state=SubjectsSG.edit),
                when=lambda data, *_: not data["missing"],
            ),
            SwitchTo(BACK, id="back", state=SubjectsSG.list),
            state=SubjectsSG.view,
            getter=view_getter,
        ),
        Window(
            Format("{text}"),
            field_buttons(SUBJECT_FIELDS, SubjectsSG.edit_field),
            field_buttons(
                {"provider": COURSE_FIELDS["provider"]}, SubjectsSG.edit_field, when="is_course"
            ),
            SwitchTo(
                Const("🗓 Year & term"), id="term", state=SubjectsSG.edit_term, when="is_subject"
            ),
            Row(
                Button(Format("{archive_label}"), id="archive", on_click=toggle_archive),
                SwitchTo(
                    Const("🗑 Delete"),
                    id="delete",
                    state=SubjectsSG.delete,
                    when="can_delete",
                    style=DANGER,
                ),
            ),
            SwitchTo(BACK, id="back", state=SubjectsSG.view),
            state=SubjectsSG.edit,
            getter=edit_getter,
        ),
        field_editor_window(
            SubjectsSG.edit_field, SubjectsSG.edit, COURSE_FIELDS, load_field, save_field
        ),
        Window(
            Format(
                "🗓 <b>Year & term</b>\n\nCurrent: <b>{current}</b>\n\n"
                "<i>The academic year is split into 3 terms.</i>"
            ),
            *_year_term_selects(on_year, on_term),
            Row(
                Button(Const("🧹 Clear"), id="clear", on_click=clear_term),
                SwitchTo(Const("✅ Done"), id="done", state=SubjectsSG.edit),
            ),
            state=SubjectsSG.edit_term,
            getter=term_getter,
        ),
        Window(
            Format("{text}"),
            Row(
                Button(Const("🗑 Yes, delete"), id="confirm", on_click=on_delete, style=DANGER),
                SwitchTo(CANCEL, id="cancel", state=SubjectsSG.edit),
            ),
            state=SubjectsSG.delete,
            getter=delete_getter,
        ),
        on_start=copy_start_data,
        on_process_result=on_result,
    )


# ------------------------------------------------------------------ create


async def create_title(message: Message, _w, manager: DialogManager) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 256:
        await message.answer("⚠️ Send a title up to 256 characters.")
        return
    manager.dialog_data["title"] = title
    if kind_of(manager) == SubjectKind.COURSE:
        await manager.switch_to(SubjectCreateSG.link)
    else:
        await manager.switch_to(SubjectCreateSG.term)


async def create_term_getter(dialog_manager: DialogManager, **_):
    year = dialog_manager.dialog_data.get("year")
    term = dialog_manager.dialog_data.get("term")
    return {
        "title": h(dialog_manager.dialog_data["title"]),
        "current": term_label(year, term) or "not set",
        "years": [{"n": y, "label": f"{'• ' if year == y else ''}Year {y}"} for y in YEARS],
        "terms": [{"n": t, "label": f"{'• ' if term == t else ''}T{t}"} for t in TERMS],
    }


async def create_year(_c: CallbackQuery, _w, manager: DialogManager, year: int) -> None:
    manager.dialog_data["year"] = year


async def create_term(_c: CallbackQuery, _w, manager: DialogManager, term: int) -> None:
    manager.dialog_data["term"] = term


async def create_link(message: Message, _w, manager: DialogManager) -> None:
    url = normalize_url(message.text or "")
    if not url:
        await message.answer("⚠️ That doesn't look like a link. Example: https://coursera.org/…")
        return
    manager.dialog_data["url"] = url
    await manager.switch_to(SubjectCreateSG.description)


async def _create(manager: DialogManager, description: str | None) -> None:
    d = manager.dialog_data
    subject = await svc(manager).subjects.create(
        kind=kind_of(manager),
        title=d["title"],
        created_by=uid(manager),
        year=d.get("year"),
        term=d.get("term"),
        url=d.get("url"),
        description=description,
    )
    await manager.done({"subject_id": subject.id})


async def create_description(message: Message, _w, manager: DialogManager) -> None:
    text = (message.text or "").strip()
    if len(text) > 4000:
        await message.answer("⚠️ Keep it under 4000 characters.")
        return
    await _create(manager, text or None)


async def skip_description(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await _create(manager, None)


async def create_title_getter(dialog_manager: DialogManager, **_):
    kind = kind_of(dialog_manager)
    example = "Programming Paradigms" if kind == SubjectKind.SUBJECT else "Deep Learning (Coursera)"
    return {"label": SUBJECT_KINDS[kind].label.lower(), "example": example}


def subject_create_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("➕ <b>New {label}</b>\n\nSend the title.\n<i>Example: {example}</i>"),
            MessageInput(create_title, content_types=["text"]),
            Cancel(CANCEL),
            state=SubjectCreateSG.title,
            getter=create_title_getter,
        ),
        Window(
            Format(
                "<b>{title}</b>\n\nWhen is it taught? Pick the study year and term.\n"
                "Selected: <b>{current}</b>"
            ),
            *_year_term_selects(create_year, create_term),
            Row(
                SwitchTo(Const("➡️ Next"), id="next", state=SubjectCreateSG.description),
                SwitchTo(Const("⏭ Skip"), id="skip", state=SubjectCreateSG.description),
            ),
            Cancel(CANCEL),
            state=SubjectCreateSG.term,
            getter=create_term_getter,
        ),
        Window(
            Const("🔗 Send the course link (Coursera, edX, …) or skip."),
            MessageInput(create_link, content_types=["text"]),
            SwitchTo(Const("⏭ Skip"), id="skip", state=SubjectCreateSG.description),
            Cancel(CANCEL),
            state=SubjectCreateSG.link,
        ),
        Window(
            Const(
                "📄 Add a short description: what it's about, grading, useful info.\n"
                "<i>You can edit everything later.</i>"
            ),
            MessageInput(create_description, content_types=["text"]),
            Button(Const("⏭ Skip & create"), id="skip", on_click=skip_description, style=PRIMARY),
            Cancel(CANCEL),
            state=SubjectCreateSG.description,
        ),
        on_start=copy_start_data,
    )
