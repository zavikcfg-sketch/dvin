from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import plans_keyboard
from core.config import get_settings
from core.services import extend_subscription, get_or_create_user

router = Router()
settings = get_settings()


@router.message(F.text == "💳 Тарифы")
async def show_plans(message: Message) -> None:
    await message.answer(
        "💳 **Тарифы VPN**\n\n"
        f"🎁 Пробный период: {settings.trial_days} дней, {settings.default_traffic_gb} ГБ\n"
        "1 месяц — 199₽\n"
        "3 месяца — 499₽ (экономия 17%)\n"
        "6 месяцев — 899₽ (экономия 25%)\n"
        "12 месяцев — 1499₽ (экономия 37%)\n\n"
        "Выберите тариф:",
        parse_mode="Markdown",
        reply_markup=plans_keyboard(),
    )


@router.callback_query(F.data.startswith("plan:"))
async def select_plan(callback: CallbackQuery, session: AsyncSession) -> None:
    parts = callback.data.split(":")
    if parts[1] == "trial":
        await callback.answer("Пробный период уже активируется при регистрации", show_alert=True)
        return

    days = int(parts[1])
    price = int(parts[2])
    await callback.message.edit_text(
        f"💳 **Оплата: {price}₽ / {days} дней**\n\n"
        "Для оплаты переведите сумму на карту:\n"
        "`2200 XXXX XXXX XXXX` (Сбербанк)\n\n"
        "В комментарии укажите ваш Telegram ID:\n"
        f"`{callback.from_user.id}`\n\n"
        "После оплаты администратор активирует подписку в течение 15 минут.\n"
        "Или напишите @support с чеком.",
        parse_mode="Markdown",
    )
    await callback.answer()
