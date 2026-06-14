import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import setup_routers
from bot.middlewares import DbSessionMiddleware
from bot.notifications import send_checkin_reminders
from core.config import get_settings
from core.database import async_session, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reminder_loop(bot: Bot) -> None:
    while True:
        await asyncio.sleep(3600)
        try:
            async with async_session() as session:
                await send_checkin_reminders(bot, session)
        except Exception:
            logger.exception("Reminder loop error")


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    await init_db()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(setup_routers())

    asyncio.create_task(reminder_loop(bot))

    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
