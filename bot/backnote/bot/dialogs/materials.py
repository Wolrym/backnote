from datetime import datetime
from urllib.parse import urlparse

from aiogram.types import CallbackQuery, Message
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
    CANCEL,
    DANGER,
    PRIMARY,
    DynamicPreview,
    can_delete,
    copy_start_data,
    data_id,
    resend,
    settings,
    svc,
    uid,
)
from backnote.bot.dialogs.states import MaterialsSG
from backnote.db.models import Material, MaterialKind
from backnote.formatting import MATERIAL_EMOJI, extract_url, fmt_datetime, h, lesson_heading


def _target(m: DialogManager) -> dict:
    return {
        "subject_id": data_id(m, "subject_id"),
        "lesson_id": data_id(m, "lesson_id"),
    }


async def _context_title(m: DialogManager) -> str:
    s = svc(m)
    if (lesson_id := data_id(m, "lesson_id")) is not None:
        return f"{h(lesson_heading(await s.lessons.get(lesson_id)))}"
    return f"{h((await s.subjects.get(data_id(m, 'subject_id'))).title)}"


async def list_getter(dialog_manager: DialogManager, **_):
    materials = await svc(dialog_manager).materials.list_for(**_target(dialog_manager))
    context = await _context_title(dialog_manager)
    if materials:
        hint = "<i>Tap an item to get the file or open the link.</i>"
    elif data_id(dialog_manager, "lesson_id"):
        hint = "<blockquote>Nothing attached yet.</blockquote>"
    else:
        hint = (
            "<blockquote>Nothing attached yet. Good candidates: syllabus, textbook, "
            "grading policy, useful links.</blockquote>"
        )
    return {
        "text": f"📎 <b>Materials</b> · {context}\n\n{hint}",
        "items": [
            {"id": m.id, "label": f"{MATERIAL_EMOJI.get(m.kind, '')} {m.title}"} for m in materials
        ],
    }


async def send_material(message_or_cb, material: Material) -> None:
    bot = message_or_cb.bot
    chat_id = (
        message_or_cb.message.chat.id
        if isinstance(message_or_cb, CallbackQuery)
        else message_or_cb.chat.id
    )
    caption = h(material.title)
    senders = {
        MaterialKind.DOCUMENT: bot.send_document,
        MaterialKind.PHOTO: bot.send_photo,
        MaterialKind.VIDEO: bot.send_video,
        MaterialKind.AUDIO: bot.send_audio,
        MaterialKind.VOICE: bot.send_voice,
    }
    send = senders.get(material.kind)
    if send and material.file_id:
        await send(chat_id, material.file_id, caption=caption)


async def on_material(callback: CallbackQuery, _w, manager: DialogManager, item: int) -> None:
    material = await svc(manager).materials.get(item)
    if material is None:
        return
    manager.dialog_data["material_id"] = item
    if material.kind != MaterialKind.LINK:
        await send_material(callback, material)
        resend(manager)
    await manager.switch_to(MaterialsSG.view)


async def view_getter(dialog_manager: DialogManager, **_):
    material = await svc(dialog_manager).materials.get(data_id(dialog_manager, "material_id"))
    if material is None:
        return {"text": "This material was deleted.", "missing": True, "preview_url": None}
    author = (
        await svc(dialog_manager).users.get(material.created_by) if material.created_by else None
    )
    lines = [f"<b>{h(material.title)}</b>"]
    if material.url:
        lines.append(f"<code>{h(material.url)}</code>")
    added = fmt_datetime(material.created_at, settings(dialog_manager).tz)
    lines.append(
        f"\n<i>Added {added}" + (f" by {h(author.display_name)}" if author else "") + "</i>"
    )
    if material.kind != MaterialKind.LINK:
        lines.append("<i>The file is sent above </i>")
    return {
        "text": "\n".join(lines),
        "missing": False,
        "url": material.url,
        "preview_url": material.url,
        "is_file": material.kind != MaterialKind.LINK,
        "can_delete": can_delete(dialog_manager, material.created_by),
    }


async def on_resend(callback: CallbackQuery, _b, manager: DialogManager) -> None:
    material = await svc(manager).materials.get(data_id(manager, "material_id"))
    if material:
        await send_material(callback, material)
        resend(manager)


def describe_message(message: Message) -> tuple[str, str | None, str | None, str] | None:
    """(kind, file_id, url, default_title) for a supported incoming message."""
    caption = (message.caption or "").strip().split("\n")[0][:200] or None
    stamp = datetime.now().strftime("%d %b")
    if message.document:
        doc = message.document
        return MaterialKind.DOCUMENT, doc.file_id, None, caption or doc.file_name or "Document"
    if message.photo:
        return MaterialKind.PHOTO, message.photo[-1].file_id, None, caption or f"Photo {stamp}"
    if message.video:
        v = message.video
        return MaterialKind.VIDEO, v.file_id, None, caption or v.file_name or f"Video {stamp}"
    if message.audio:
        a = message.audio
        title = caption or a.title or a.file_name or f"Audio {stamp}"
        return MaterialKind.AUDIO, a.file_id, None, title
    if message.voice:
        return MaterialKind.VOICE, message.voice.file_id, None, caption or f"Voice {stamp}"
    url = extract_url(message)
    if url:
        text = (message.text or "").replace(url, "").strip().split("\n")[0][:200]
        return MaterialKind.LINK, None, url, text or urlparse(url).hostname or url
    return None


async def on_add_input(message: Message, _w, manager: DialogManager) -> None:
    described = describe_message(message)
    if described is None:
        await message.answer(
            "⚠️ Send a file (PDF, slides, photo, video, audio) or a message with a link."
        )
        return
    kind, file_id, url, title = described
    material = await svc(manager).materials.create(
        **_target(manager),
        kind=kind,
        title=title,
        url=url,
        file_id=file_id,
        created_by=uid(manager),
    )
    manager.dialog_data["material_id"] = material.id
    manager.dialog_data["added"] = manager.dialog_data.get("added", 0) + 1


async def add_getter(dialog_manager: DialogManager, **_):
    added = dialog_manager.dialog_data.get("added", 0)
    last = None
    if added and (mid := data_id(dialog_manager, "material_id")):
        last = await svc(dialog_manager).materials.get(mid)
    status = (
        f"\n\nAdded {added} item(s). Last: <b>{h(last.title)}</b>\n"
        "<i>Send more, rename the last one, or finish.</i>"
        if last
        else ""
    )
    return {
        "text": (
            "📎 <b>Add materials</b>\n\nSend files (PDF, slides, photos, video, audio) or links. "
            "Several at once is fine; the caption or file name becomes the title." + status
        ),
        "has_last": last is not None,
    }


async def finish_adding(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    manager.dialog_data.pop("added", None)
    await manager.switch_to(MaterialsSG.list)


async def start_rename_last(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    manager.dialog_data["rename_back"] = "add"
    await manager.switch_to(MaterialsSG.rename)


async def start_rename(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    manager.dialog_data["rename_back"] = "view"
    await manager.switch_to(MaterialsSG.rename)


def _rename_back_state(manager: DialogManager):
    return MaterialsSG.add if manager.dialog_data.get("rename_back") == "add" else MaterialsSG.view


async def on_rename(message: Message, _w, manager: DialogManager) -> None:
    title = (message.text or "").strip()
    if not title or len(title) > 256:
        await message.answer("⚠️ Send a title up to 256 characters.")
        return
    await svc(manager).materials.rename(data_id(manager, "material_id"), title)
    await manager.switch_to(_rename_back_state(manager))


async def cancel_rename(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await manager.switch_to(_rename_back_state(manager))


async def rename_getter(dialog_manager: DialogManager, **_):
    material = await svc(dialog_manager).materials.get(data_id(dialog_manager, "material_id"))
    return {"title": h(material.title)}


async def on_delete(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    material = await svc(manager).materials.get(data_id(manager, "material_id"))
    if material and can_delete(manager, material.created_by):
        await svc(manager).materials.delete(material.id)
    await manager.switch_to(MaterialsSG.list)


def materials_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{text}"),
            ScrollingGroup(
                Select(
                    Format("{item[label]}"),
                    id="material",
                    item_id_getter=lambda x: x["id"],
                    items="items",
                    type_factory=int,
                    on_click=on_material,
                ),
                id="materials_scroll",
                width=1,
                height=8,
                hide_on_single_page=True,
            ),
            SwitchTo(Const("➕ Add"), id="add", state=MaterialsSG.add, style=PRIMARY),
            Cancel(BACK),
            state=MaterialsSG.list,
            getter=list_getter,
        ),
        Window(
            Format("{text}"),
            MessageInput(on_add_input),
            Button(
                Const("✏️ Rename last"), id="rename", on_click=start_rename_last, when="has_last"
            ),
            Button(Const("✅ Done"), id="done", on_click=finish_adding),
            state=MaterialsSG.add,
            getter=add_getter,
        ),
        Window(
            Format("{text}"),
            DynamicPreview(),
            Url(Const("🔗 Open link"), Format("{url}"), when="url"),
            Button(Const("📤 Send again"), id="resend", on_click=on_resend, when="is_file"),
            Row(
                Button(
                    Const("✏️ Rename"),
                    id="rename",
                    on_click=start_rename,
                    when=lambda d, *_: not d["missing"],
                ),
                SwitchTo(
                    Const("🗑 Delete"),
                    id="delete",
                    state=MaterialsSG.delete,
                    when="can_delete",
                    style=DANGER,
                ),
            ),
            SwitchTo(BACK, id="back", state=MaterialsSG.list),
            state=MaterialsSG.view,
            getter=view_getter,
        ),
        Window(
            Format("✏️ Current title: <b>{title}</b>\n\nSend a new title."),
            MessageInput(on_rename, content_types=["text"]),
            Button(CANCEL, id="cancel", on_click=cancel_rename),
            state=MaterialsSG.rename,
            getter=rename_getter,
        ),
        Window(
            Const("🗑 Delete this material for everyone?"),
            Row(
                Button(Const("🗑 Yes, delete"), id="confirm", on_click=on_delete, style=DANGER),
                SwitchTo(CANCEL, id="cancel", state=MaterialsSG.view),
            ),
            state=MaterialsSG.delete,
        ),
        on_start=copy_start_data,
    )
