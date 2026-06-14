from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import admin_menu, main_menu
from core.config import get_settings
from core.models import Subscription, SubscriptionStatus, User, VpnServer
from core.services import extend_subscription, get_or_create_user

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
    active_subs = await session.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
        )
    )
    servers = await session.execute(select(VpnServer))
    server_list = list(servers.scalars().all())
    server_info = "\n".join(
        f"  • {s.name}: {s.current_users}/{s.max_users} ({s.status.value})" for s in server_list
    ) or "  Нет серверов"

    await message.answer(
        f"📈 **Статистика**\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"✅ Активных подписок: {active_subs}\n\n"
        f"🖥 **Серверы:**\n{server_info}",
        parse_mode="Markdown",
    )


@router.message(F.text == "🖥 Серверы")
async def list_servers(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    result = await session.execute(select(VpnServer))
    servers = list(result.scalars().all())
    if not servers:
        await message.answer(
            "Серверов нет. Добавьте через админ-панель:\n"
            "http://localhost:8080/admin/servers"
        )
        return
    lines = []
    for s in servers:
        lines.append(
            f"**{s.name}** ({s.country})\n"
            f"  Host: `{s.host}:{s.port}`\n"
            f"  SNI: {s.sni}\n"
            f"  Users: {s.current_users}/{s.max_users}\n"
            f"  Status: {s.status.value}"
        )
    await message.answer("\n\n".join(lines), parse_mode="Markdown")


@router.message(Command("grant"))
async def grant_subscription(message: Message, session: AsyncSession) -> None:
    """Usage: /grant <telegram_id> <days>"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /grant <telegram_id> <дней>")
        return
    try:
        tg_id = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await message.answer("Неверный формат")
        return

    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer(f"Пользователь {tg_id} не найден")
        return

    await extend_subscription(session, user, days)
    await message.answer(f"✅ Подписка продлена на {days} дней для {tg_id}")
