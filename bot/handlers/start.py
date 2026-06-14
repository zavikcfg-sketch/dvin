from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import main_menu
from core.config import get_settings
from core.services import get_or_create_user

router = Router()
settings = get_settings()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    is_admin = message.from_user.id in settings.admin_id_list
    text = (
        f"Привет, {message.from_user.first_name or 'друг'}! 👋\n\n"
        "Бот посуточного бронирования с интеграцией **TVIL**.\n\n"
        "📅 **Забронировать** — выбор номера и дат\n"
        "🗓 **Свободные даты** — календарь доступности\n"
        "📋 **Мои брони** — ваши заявки\n"
        "❓ **Помощь** — как это работает"
    )
    if is_admin:
        text += "\n\n🛠 Админ: /admin"
    await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")


@router.message(F.text == "❓ Помощь")
async def help_message(message: Message) -> None:
    await message.answer(
        "**Как забронировать:**\n\n"
        "1. Нажмите 📅 **Забронировать**\n"
        "2. Выберите номер и даты заезда/выезда\n"
        "3. Подтвердите заявку\n"
        "4. Администратор подтвердит бронь\n\n"
        "**TVIL:** после заявки можно перейти на сайт TVIL для оплаты.\n"
        "Занятость синхронизируется с TVIL — двойные брони исключены.",
        parse_mode="Markdown",
    )
