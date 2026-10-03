import logging
from functools import partial

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, ExceptionTypeFilter
from aiogram.types import CallbackQuery, ErrorEvent, Message
from aiogram_dialog import BgManagerFactory, DialogManager, ShowMode, StartMode
from aiogram_dialog.api.exceptions import OutdatedIntent, UnknownIntent, UnknownState

from backnote.bot.callbacks import AccessCb, OpenCb
from backnote.bot.dialogs.states import LessonsSG, MainSG
from backnote.bot.dialogs.summary import send_summary
from backnote.config import Settings
from backnote.db.models import UserStatus
from backnote.formatting import h
from backnote.services import Services

log = logging.getLogger(__name__)


async def open_target(manager: DialogManager, svc: Services, target: str, obj_id: int) -> bool:
    """Open a lesson on top of a fresh main menu, so Back leads somewhere useful."""
    if target == "lesson":
        obj = await svc.lessons.get(obj_id)
        state, data = LessonsSG.view, {"lesson_id": obj_id}
    else:
        return False
    if obj is None:
        return False
    data["subject_id"] = obj.subject_id
    await manager.start(MainSG.menu, mode=StartMode.RESET_STACK, show_mode=ShowMode.NO_UPDATE)
    await manager.start(state, data=data, show_mode=ShowMode.SEND)
    return True


DEEP_LINK_PREFIXES = {"l": "lesson"}


async def cmd_start(
    message: Message, command: CommandObject, dialog_manager: DialogManager, svc: Services
) -> None:
    payload = command.args or ""
    if payload[:1] in DEEP_LINK_PREFIXES and payload[1:].isdigit():
        target = DEEP_LINK_PREFIXES[payload[0]]
        if await open_target(dialog_manager, svc, target, int(payload[1:])):
            return
        await message.answer("That item no longer exists.")
    await dialog_manager.start(MainSG.menu, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def cmd_menu(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(MainSG.menu, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def cmd_help(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(MainSG.help, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def cmd_id(message: Message) -> None:
    await message.answer(f"🆔 Your Telegram ID: <code>{message.from_user.id}</code>")


async def on_open(
    callback: CallbackQuery,
    callback_data: OpenCb,
    dialog_manager: DialogManager,
    svc: Services,
    settings: Settings,
) -> None:
    if callback_data.target == "summary":
        sent = await send_summary(
            callback.bot, svc, settings.tz, callback.message.chat.id, callback_data.id
        )
        await callback.answer(None if sent else "The summary is gone.")
        return
    opened = await open_target(dialog_manager, svc, callback_data.target, callback_data.id)
    await callback.answer(None if opened else "This item no longer exists.")


async def on_access_decision(
    callback: CallbackQuery, callback_data: AccessCb, svc: Services, settings: Settings
) -> None:
    if callback.from_user.id != settings.admin_id:
        await callback.answer("Only the admin can do this.", show_alert=True)
        return
    if callback_data.action == "allow":
        user = await svc.users.allow(callback_data.user_id)
        verdict = "Allowed"
        try:
            await callback.bot.send_message(
                user.id,
                "<b>You now have access to Backnote.</b>\nPress /start to open the menu.",
            )
        except Exception:
            log.info("Could not notify %s about access", user.id)
    else:
        user = await svc.users.set_status(callback_data.user_id, UserStatus.BLOCKED)
        verdict = "Blocked"
    name = h(user.display_name) if user else callback_data.user_id
    await callback.message.edit_text(f"{callback.message.html_text}\n\n<b>{verdict}</b>: {name}")
    await callback.answer()


async def fallback(message: Message, dialog_manager: DialogManager) -> None:
    """Text that no dialog step consumed just brings the menu back."""
    await dialog_manager.start(MainSG.menu, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


async def on_stale_dialog(event: ErrorEvent, bg_factory: BgManagerFactory) -> None:
    """Buttons from before a restart point to lost dialog state — start over gracefully.

    Error events are not chat events, so `dialog_manager` is unavailable here and a background
    manager addresses the chat directly instead.
    """
    log.info("Restarting dialog after %r", event.exception)
    callback = event.update.callback_query
    if callback:
        await callback.answer("This menu is outdated — opening a fresh one.")
    message = callback.message if callback else event.update.message
    if message is None or message.from_user is None:
        return
    await bg_factory.bg(
        bot=message.bot, user_id=message.from_user.id, chat_id=message.chat.id
    ).start(MainSG.menu, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND)


def build_routers(bg_factory: BgManagerFactory) -> tuple[Router, Router, Router]:
    """(errors, commands, fallback) — fresh instances, since a router attaches to one parent."""
    errors = Router(name="errors")
    errors.error.register(
        partial(on_stale_dialog, bg_factory=bg_factory),
        ExceptionTypeFilter(UnknownIntent, OutdatedIntent, UnknownState),
    )

    commands = Router(name="commands")
    commands.message.register(cmd_start, CommandStart())
    commands.message.register(cmd_menu, Command("menu"))
    commands.message.register(cmd_help, Command("help"))
    commands.message.register(cmd_id, Command("id"))
    commands.callback_query.register(on_open, OpenCb.filter())
    commands.callback_query.register(on_access_decision, AccessCb.filter())

    fallback_router = Router(name="fallback")
    fallback_router.message.register(fallback, F.text)
    return errors, commands, fallback_router
