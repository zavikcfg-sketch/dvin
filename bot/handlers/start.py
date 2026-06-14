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
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    is_admin = message.from_user.id in settings.admin_id_list
    text = (
        f"Привет, {message.from_user.first_name or 'друг'}! 👋\n\n"
        "Это VPN-сервис для обхода блокировок и белых списков.\n"
        "Протокол: **VLESS + Reality** — трафик маскируется под обычный HTTPS.\n\n"
        "🔑 **Мой VPN** — получить ключ подключения\n"
        "📊 **Статус** — подписка и трафик\n"
        "💳 **Тарифы** — продлить доступ\n"
        "🏨 **Бронирование** — посуточное бронирование номеров\n"
        "❓ **Помощь** — инструкция по настройке"
    )
    if is_admin:
        text += "\n\n🛠 У вас есть права администратора. /admin"
    await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")


@router.message(F.text == "❓ Помощь")
async def help_message(message: Message) -> None:
    await message.answer(
        "**Как подключиться:**\n\n"
        "1. Нажмите 🔑 **Мой VPN** и выберите сервер\n"
        "2. Скопируйте ссылку или отсканируйте QR-код\n"
        "3. Импортируйте в приложение:\n"
        "   • Android: [Hiddify](https://play.google.com/store/apps/details?id=app.hiddify.com)\n"
        "   • iOS: Streisand / V2Box\n"
        "   • Windows: [v2rayN](https://github.com/2dust/v2rayN)\n"
        "   • macOS: V2Box / FoXray\n\n"
        "**Если не работает:**\n"
        "• Попробуйте другой сервер\n"
        "• Обновите приложение\n"
        "• Напишите в поддержку: @support",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
