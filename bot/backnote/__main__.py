import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, LinkPreviewOptions

from backnote.bot.factory import build_dispatcher
from backnote.bot.notifier import Notifier
from backnote.config import Settings
from backnote.db import create_engine, create_sessionmaker
from backnote.db.migrate import upgrade
from backnote.services import Services

COMMANDS = [
    BotCommand(command="start", description="Main menu"),
    BotCommand(command="help", description="How it works"),
    BotCommand(command="id", description="Show your Telegram ID"),
]


async def run(settings: Settings) -> None:
    engine = create_engine(settings.database_url)
    services = Services.create(create_sessionmaker(engine), settings.admin_id)
    bot = Bot(
        settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview=LinkPreviewOptions(is_disabled=True),
        ),
    )
    try:
        me = await bot.get_me()
        notifier = Notifier(bot, services, settings.tz)
        dp = build_dispatcher(settings, services, notifier, bot_username=me.username)
        await bot.set_my_commands(COMMANDS)
        logging.info("Starting @%s (AI summaries: %s)", me.username, settings.ai_enabled)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = Settings()
    # Alembic's async env runs its own event loop, so migrate before starting ours.
    upgrade(settings.database_url)
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
