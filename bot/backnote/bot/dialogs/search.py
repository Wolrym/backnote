from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Cancel, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from backnote.bot.dialogs.common import BACK, svc
from backnote.bot.dialogs.states import LessonsSG, SearchSG, SubjectsSG
from backnote.formatting import SUBJECT_KINDS, h, lesson_code


async def on_query(message: Message, _w, manager: DialogManager) -> None:
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("⚠️ Type at least 2 characters.")
        return
    manager.dialog_data["q"] = query[:100]
    await manager.switch_to(SearchSG.results)


async def results_getter(dialog_manager: DialogManager, **_):
    query = dialog_manager.dialog_data["q"]
    s = svc(dialog_manager)
    subjects = await s.subjects.search(query)
    lessons = await s.lessons.search(query)
    items = [
        {
            "id": f"s:{subj.kind}:{subj.id}",
            "label": f"{SUBJECT_KINDS[subj.kind].label}: {subj.title}",
        }
        for subj in subjects
    ] + [
        {
            "id": f"l:{subj.id}:{lesson.id}",
            "label": f"{lesson_code(lesson)} · {lesson.title} — {subj.title}",
        }
        for lesson, subj in lessons
    ]
    if items:
        text = (
            f"Results for <b>“{h(query)}”</b>\n"
            f"<blockquote>{len(subjects)} subjects/courses · {len(lessons)} lessons</blockquote>\n"
            "<i>Lessons are matched by title, description and summary.</i>"
        )
    else:
        text = f"Nothing found for <b>“{h(query)}”</b>. Try another word."
    return {"text": text, "items": items}


async def on_result(_c: CallbackQuery, _w, manager: DialogManager, item_id: str) -> None:
    kind, a, b = item_id.split(":")
    if kind == "s":
        await manager.start(SubjectsSG.view, data={"kind": a, "subject_id": int(b)})
    else:
        await manager.start(LessonsSG.view, data={"subject_id": int(a), "lesson_id": int(b)})


def search_dialog() -> Dialog:
    return Dialog(
        Window(
            Const(
                "<b>Search</b>\n\nSend a word or phrase — I'll look through subjects, courses, "
                "lesson titles, descriptions and summaries."
            ),
            MessageInput(on_query, content_types=["text"]),
            Cancel(BACK),
            state=SearchSG.query,
        ),
        Window(
            Format("{text}"),
            ScrollingGroup(
                Select(
                    Format("{item[label]}"),
                    id="result",
                    item_id_getter=lambda x: x["id"],
                    items="items",
                    on_click=on_result,
                ),
                id="results_scroll",
                width=1,
                height=8,
                hide_on_single_page=True,
            ),
            MessageInput(on_query, content_types=["text"]),
            SwitchTo(Const("🔁 New search"), id="again", state=SearchSG.query),
            Cancel(BACK),
            state=SearchSG.results,
            getter=results_getter,
        ),
    )
