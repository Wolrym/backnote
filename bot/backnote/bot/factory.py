from aiogram import Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs
from aiogram_dialog.api.protocols import MessageManagerProtocol

from backnote.ai import GeminiSummarizer
from backnote.bot.dialogs import all_dialogs
from backnote.bot.handlers import build_routers
from backnote.bot.middlewares import AccessMiddleware
from backnote.bot.notifier import Notifier
from backnote.config import Settings
from backnote.services import Services


def build_dispatcher(
    settings: Settings,
    services: Services,
    notifier: Notifier,
    *,
    bot_username: str,
    storage: BaseStorage | None = None,
    message_manager: MessageManagerProtocol | None = None,
) -> Dispatcher:
    dp = Dispatcher(storage=storage or MemoryStorage())
    dp["settings"] = settings
    dp["svc"] = services
    dp["notifier"] = notifier
    dp["bot_username"] = bot_username
    dp["summarizer"] = (
        GeminiSummarizer(
            settings.gemini_api_key.get_secret_value(),
            settings.gemini_model,
            settings.summary_language,
        )
        if settings.ai_enabled
        else None
    )

    access = AccessMiddleware()
    dp.message.outer_middleware(access)
    dp.callback_query.outer_middleware(access)

    # Commands go first so /start works everywhere; the catch-all goes last so dialog inputs win.
    # setup_dialogs first, so its background-manager factory can be handed to the error handler.
    bg_factory = setup_dialogs(dp, message_manager=message_manager)
    errors, commands, fallback = build_routers(bg_factory)
    dp.include_routers(errors, commands, *all_dialogs(), fallback)
    return dp
