from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import admin_menu, main_menu
from core.config import get_settings
from core.models import BookingStatus, RoomBooking, User

router = Router()
settings = get_settings()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_id_list


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer("🛠 **Панель администратора**", parse_mode="Markdown", reply_markup=admin_menu())


@router.message(F.text == "◀️ Главное меню")
async def back_to_main(message: Message) -> None:
    await message.answer("Главное меню", reply_markup=main_menu())


@router.message(F.text == "📈 Статистика")
async def stats(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    users_count = await session.scalar(select(func.count(User.id)))
    pending = await session.scalar(
        select(func.count(RoomBooking.id)).where(RoomBooking.status == BookingStatus.PENDING)
    )
    confirmed = await session.scalar(
        select(func.count(RoomBooking.id)).where(RoomBooking.status == BookingStatus.CONFIRMED)
    )

    await message.answer(
        f"📈 **Статистика**\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"⏳ Ожидают подтверждения: {pending}\n"
        f"✅ Подтверждено: {confirmed}",
        parse_mode="Markdown",
    )
