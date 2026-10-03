import asyncio

from aiogram.types import CallbackQuery, Message, MessageOriginUser
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from backnote.bot.dialogs.common import (
    BACK,
    CANCEL,
    DANGER,
    PRIMARY,
    SUCCESS,
    data_id,
    notifier,
    settings,
    svc,
    uid,
)
from backnote.bot.dialogs.states import AdminSG
from backnote.db.models import UserStatus
from backnote.formatting import fmt_datetime, h

STATUS_EMOJI = {UserStatus.ACTIVE: "", UserStatus.PENDING: "", UserStatus.BLOCKED: ""}


async def menu_getter(dialog_manager: DialogManager, **_):
    users = await svc(dialog_manager).users.list_users()
    counts = {status: sum(u.status == status for u in users) for status in UserStatus}
    return {
        "text": (
            "🛡 <b>Admin panel</b>\n"
            f"<blockquote>{counts[UserStatus.ACTIVE]} members · "
            f"{counts[UserStatus.PENDING]} requests · "
            f"{counts[UserStatus.BLOCKED]} blocked</blockquote>\n"
            "<i>Only whitelisted members can use the bot. New people who press /start "
            "appear as requests.</i>"
        ),
        "requests_label": f"⏳ Requests ({counts[UserStatus.PENDING]})",
    }


def _set_filter(status: str | None):
    async def handler(_c: CallbackQuery, _b, manager: DialogManager) -> None:
        manager.dialog_data["filter"] = status
        await manager.switch_to(AdminSG.users)

    return handler


async def users_getter(dialog_manager: DialogManager, **_):
    status = dialog_manager.dialog_data.get("filter")
    users = await svc(dialog_manager).users.list_users(UserStatus(status) if status else None)
    title = "<b>Access requests</b>" if status == UserStatus.PENDING else "<b>People</b>"
    body = "" if users else "\n\n<blockquote>Nobody here.</blockquote>"
    return {
        "text": title + body,
        "items": [
            {
                "id": u.id,
                "label": f"{STATUS_EMOJI.get(u.status, '')} {u.display_name}"
                + (" " if u.id == settings(dialog_manager).admin_id else ""),
            }
            for u in users
        ],
    }


async def on_user(_c: CallbackQuery, _w, manager: DialogManager, user_id: int) -> None:
    manager.dialog_data["user_id"] = user_id
    await manager.switch_to(AdminSG.user)


async def user_getter(dialog_manager: DialogManager, **_):
    tz = settings(dialog_manager).tz
    user = await svc(dialog_manager).users.get(data_id(dialog_manager, "user_id"))
    if user is None:
        return {
            "text": "User removed.",
            "can_allow": False,
            "can_block": False,
            "can_remove": False,
        }
    is_owner = user.id == settings(dialog_manager).admin_id
    lines = [
        f"{STATUS_EMOJI.get(user.status, '')} <b>{h(user.display_name)}</b>",
        f"🆔 <code>{user.id}</code>",
    ]
    if user.username:
        lines.append(f"@{h(user.username)}")
    lines.append(f"Status: <b>{user.status}</b>" + (" · admin" if is_owner else ""))
    lines.append(f"Joined: {fmt_datetime(user.created_at, tz)}")
    if user.last_seen_at:
        lines.append(f"Last seen: {fmt_datetime(user.last_seen_at, tz)}")
    return {
        "text": "\n".join(lines),
        "can_allow": user.status != UserStatus.ACTIVE,
        "can_block": not is_owner and user.status != UserStatus.BLOCKED,
        "can_remove": not is_owner,
    }


async def _notify_granted(manager: DialogManager, user_id: int) -> None:
    await notifier(manager).send(
        user_id, "<b>You now have access to Backnote.</b>\nPress /start to open the menu.", None
    )


async def on_allow(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    user_id = data_id(manager, "user_id")
    await svc(manager).users.allow(user_id)
    await _notify_granted(manager, user_id)


async def on_block(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await svc(manager).users.set_status(data_id(manager, "user_id"), UserStatus.BLOCKED)


async def on_remove(_c: CallbackQuery, _b, manager: DialogManager) -> None:
    await svc(manager).users.remove(data_id(manager, "user_id"))
    await manager.switch_to(AdminSG.users)


def parse_user_id(message: Message) -> int | None:
    if message.contact and message.contact.user_id:
        return message.contact.user_id
    if isinstance(message.forward_origin, MessageOriginUser):
        return message.forward_origin.sender_user.id
    if message.users_shared and message.users_shared.users:
        return message.users_shared.users[0].user_id
    text = (message.text or "").strip()
    return int(text) if text.isdigit() else None


async def on_add_input(message: Message, _w, manager: DialogManager) -> None:
    user_id = parse_user_id(message)
    if user_id is None:
        await message.answer(
            "⚠️ I couldn't get a user id from that. If a forwarded message doesn't work, the "
            "person hides their account in forwards — ask them to send /id to the bot."
        )
        return
    await svc(manager).users.allow(user_id)
    await _notify_granted(manager, user_id)
    manager.dialog_data["user_id"] = user_id
    await manager.switch_to(AdminSG.user)


async def on_broadcast_text(message: Message, _w, manager: DialogManager) -> None:
    if not message.text:
        await message.answer("⚠️ Send text.")
        return
    manager.dialog_data["broadcast"] = message.html_text
    await manager.switch_to(AdminSG.broadcast_confirm)


async def broadcast_getter(dialog_manager: DialogManager, **_):
    recipients = await svc(dialog_manager).users.active_ids(exclude=uid(dialog_manager))
    return {
        "preview": dialog_manager.dialog_data.get("broadcast", ""),
        "count": len(recipients),
    }


async def on_broadcast_send(callback: CallbackQuery, _b, manager: DialogManager) -> None:
    text = "<b>Announcement</b>\n\n" + manager.dialog_data.pop("broadcast", "")
    n = notifier(manager)
    recipients = await svc(manager).users.active_ids(exclude=uid(manager))

    async def run() -> None:
        for user_id in recipients:
            await n.send(user_id, text, None)
            await asyncio.sleep(0.05)

    n.run(run())
    await callback.answer(f"Sending to {len(recipients)} member(s)…")
    await manager.switch_to(AdminSG.menu)


def admin_dialog() -> Dialog:
    return Dialog(
        Window(
            Format("{text}"),
            Row(
                Button(Const("👥 Everyone"), id="all", on_click=_set_filter(None)),
                Button(
                    Format("{requests_label}"),
                    id="pending",
                    on_click=_set_filter(UserStatus.PENDING.value),
                ),
            ),
            Row(
                SwitchTo(Const("➕ Add member"), id="add", state=AdminSG.add, style=PRIMARY),
                SwitchTo(Const("📣 Broadcast"), id="broadcast", state=AdminSG.broadcast),
            ),
            Cancel(BACK),
            state=AdminSG.menu,
            getter=menu_getter,
        ),
        Window(
            Format("{text}"),
            ScrollingGroup(
                Select(
                    Format("{item[label]}"),
                    id="user",
                    item_id_getter=lambda x: x["id"],
                    items="items",
                    type_factory=int,
                    on_click=on_user,
                ),
                id="users_scroll",
                width=1,
                height=8,
                hide_on_single_page=True,
            ),
            SwitchTo(BACK, id="back", state=AdminSG.menu),
            state=AdminSG.users,
            getter=users_getter,
        ),
        Window(
            Format("{text}"),
            Row(
                Button(
                    Const("✅ Allow"),
                    id="allow",
                    on_click=on_allow,
                    when="can_allow",
                    style=SUCCESS,
                ),
                Button(Const("⛔ Block"), id="block", on_click=on_block, when="can_block"),
            ),
            Button(
                Const("🗑 Remove"), id="remove", on_click=on_remove, when="can_remove", style=DANGER
            ),
            SwitchTo(BACK, id="back", state=AdminSG.users),
            state=AdminSG.user,
            getter=user_getter,
        ),
        Window(
            Const(
                "<b>Add a member</b>\n\nSend one of:\n• their numeric Telegram ID "
                "(they can get it with /id)\n• their contact\n• a message forwarded from them"
            ),
            MessageInput(on_add_input),
            SwitchTo(CANCEL, id="cancel", state=AdminSG.menu),
            state=AdminSG.add,
        ),
        Window(
            Const("<b>Broadcast</b>\n\nSend the message for all members. Formatting is kept."),
            MessageInput(on_broadcast_text, content_types=["text"]),
            SwitchTo(CANCEL, id="cancel", state=AdminSG.menu),
            state=AdminSG.broadcast,
        ),
        Window(
            Format("Send this to <b>{count}</b> member(s)?\n\n<blockquote>{preview}</blockquote>"),
            Row(
                Button(Const("📤 Send"), id="send", on_click=on_broadcast_send, style=PRIMARY),
                SwitchTo(CANCEL, id="cancel", state=AdminSG.menu),
            ),
            state=AdminSG.broadcast_confirm,
            getter=broadcast_getter,
        ),
    )
