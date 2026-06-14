from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin import is_admin
from bot.keyboards import admin_bookings_keyboard, admin_rooms_keyboard
from bot.notifications import (
    notify_admins_tvil_export,
    notify_user_booking_confirmed,
    notify_user_booking_rejected,
)
from bot.states import TvilImportStates
from core.booking_services import (
    add_room,
    cancel_booking,
    confirm_booking,
    format_booking,
    get_all_bookings,
    get_booking,
    get_room,
    set_room_active,
)
from core.config import get_settings
from core.models import BookingStatus, Room
from core.tvil_service import (
    build_tvil_owner_calendar_url,
    import_tvil_blocks_text,
    mark_tvil_exported,
)

router = Router()
settings = get_settings()


@router.message(F.text == "🏠 Комнаты")
async def admin_rooms(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    result = await session.execute(select(Room).order_by(Room.name))
    rooms = list(result.scalars().all())
    if not rooms:
        await message.answer(
            "Комнат нет.\n\n"
            "Добавить: `/add_room Название | описание | цена_за_ночь`\n"
            "Пример: `/add_room Стандарт | Двухместный номер | 3500`",
            parse_mode="Markdown",
        )
        return
    lines = []
    for room in rooms:
        status = "активна" if room.is_active else "скрыта"
        price = f"{room.price_per_night}₽/ночь" if room.price_per_night else "цена не указана"
        tvil = f"🔗 TVIL `{room.tvil_object_id}`" if room.tvil_object_id else ""
        lines.append(f"**#{room.id} {room.name}** ({status}) {tvil}\n  {price}")
    await message.answer(
        "\n\n".join(lines)
        + "\n\nTVIL: `/set_tvil ID | object_id | ссылка`\n"
        "Импорт занятости: `/tvil_import ID`\n"
        "Инструкция: `/tvil`",
        parse_mode="Markdown",
        reply_markup=admin_rooms_keyboard(rooms),
    )


@router.message(Command("add_room"))
async def cmd_add_room(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("/add_room", "", 1).strip()
    if not text:
        await message.answer(
            "Использование: `/add_room Название | описание | цена`\n"
            "Пример: `/add_room Люкс | Номер с видом | 5000`",
            parse_mode="Markdown",
        )
        return
    parts = [p.strip() for p in text.split("|")]
    name = parts[0]
    description = parts[1] if len(parts) > 1 else None
    price = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    room = await add_room(session, name, description, price)
    await message.answer(f"✅ Комната **{room.name}** (#{room.id}) добавлена.", parse_mode="Markdown")


@router.callback_query(F.data.startswith("aroom:toggle:"))
async def toggle_room(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    room_id = int(callback.data.split(":")[2])
    room = await get_room(session, room_id)
    if not room:
        await callback.answer("Не найдена", show_alert=True)
        return
    await set_room_active(session, room, not room.is_active)
    status = "активна" if room.is_active else "скрыта"
    await callback.answer(f"{room.name}: {status}")
    result = await session.execute(select(Room).order_by(Room.name))
    rooms = list(result.scalars().all())
    await callback.message.edit_reply_markup(reply_markup=admin_rooms_keyboard(rooms))


@router.message(Command("set_tvil"))
async def cmd_set_tvil(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("/set_tvil", "", 1).strip()
    if not text or "|" not in text:
        await message.answer(
            "Использование:\n"
            "`/set_tvil ID | object_id_на_tvil | ссылка_на_объявление`\n\n"
            "Пример:\n"
            "`/set_tvil 1 | 123456 | https://tvil.ru/...`",
            parse_mode="Markdown",
        )
        return

    parts = [p.strip() for p in text.split("|")]
    if not parts[0].isdigit():
        await message.answer("Первый параметр — числовой ID комнаты.")
        return

    room = await get_room(session, int(parts[0]))
    if not room:
        await message.answer("Комната не найдена.")
        return

    if len(parts) > 1 and parts[1]:
        room.tvil_object_id = parts[1]
    if len(parts) > 2 and parts[2]:
        room.tvil_listing_url = parts[2]
    await session.commit()
    await session.refresh(room)

    lines = [
        f"✅ TVIL настроен для **{room.name}** (#{room.id})",
        f"🆔 Object ID: `{room.tvil_object_id or '—'}`",
    ]
    if room.tvil_listing_url:
        lines.append(f"🌐 Объявление: {room.tvil_listing_url}")
    if settings.public_base_url and settings.tvil_webhook_secret:
        base = settings.public_base_url.rstrip("/")
        lines.append(f"📥 Webhook: `{base}/webhooks/tvil/blocks`")
        lines.append(f"📤 Экспорт: `{base}/api/tvil/pending?secret=...`")
    else:
        lines.append("⚠️ Задайте `PUBLIC_BASE_URL` и `TVIL_WEBHOOK_SECRET` в `.env` для HTTP API.")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("tvil"))
async def cmd_tvil_help(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    base = settings.public_base_url.rstrip("/") if settings.public_base_url else "https://ваш-домен.com"
    await message.answer(
        "🔗 **Интеграция с TVIL (без iCal и без API)**\n\n"
        "**1. Настройка объекта**\n"
        "`/set_tvil ID | object_id | ссылка_на_объявление`\n"
        "Object ID — в личном кабинете TVIL: **Мои объекты**.\n\n"
        "**2. Импорт занятости с TVIL → бот**\n"
        "• Вручную: `/tvil_import ID`, затем вставьте периоды:\n"
        "  `14.06.2025-16.06.2025`\n"
        "• Через HTTP (n8n, скрипт):\n"
        f"`POST {base}/webhooks/tvil/blocks`\n"
        "```json\n"
        '{"secret":"...","room_id":1,"blocks":[{"check_in":"2025-06-14","check_out":"2025-06-16"}]}\n'
        "```\n\n"
        "**3. Экспорт занятости из бота → TVIL**\n"
        "После подтверждения брони бот пришлёт даты для закрытия в календаре TVIL.\n"
        f"Календарь: {build_tvil_owner_calendar_url()}\n\n"
        f"Автоматизация: `GET {base}/api/tvil/pending?secret=...`",
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


@router.message(Command("tvil_import"))
async def cmd_tvil_import(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("/tvil_import", "", 1).strip()
    if not text.isdigit():
        await message.answer("Использование: `/tvil_import ID_комнаты`", parse_mode="Markdown")
        return
    room = await get_room(session, int(text))
    if not room:
        await message.answer("Комната не найдена.")
        return
    await state.set_state(TvilImportStates.waiting_periods)
    await state.update_data(room_id=room.id)
    await message.answer(
        f"Вставьте занятые периоды для **{room.name}** (по одному на строку):\n\n"
        "`14.06.2025-16.06.2025`\n"
        "`20.07.2025-25.07.2025`",
        parse_mode="Markdown",
    )


@router.message(TvilImportStates.waiting_periods)
async def tvil_import_periods(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    room = await get_room(session, data["room_id"])
    if not room:
        await state.clear()
        await message.answer("Комната не найдена.")
        return
    try:
        count = await import_tvil_blocks_text(session, room, message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.clear()
    await message.answer(f"✅ Импортировано {count} период(ов) с TVIL для **{room.name}**.", parse_mode="Markdown")


@router.message(Command("tvil_done"))
async def cmd_tvil_done(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("/tvil_done", "", 1).strip()
    if not text.isdigit():
        await message.answer("Использование: `/tvil_done ID_брони`", parse_mode="Markdown")
        return
    booking = await get_booking(session, int(text))
    if not booking:
        await message.answer("Бронирование не найдено.")
        return
    await mark_tvil_exported(session, booking)
    await message.answer(f"✅ Бронь #{booking.id} отмечена как выгруженная на TVIL.")


@router.message(F.text == "📅 Брони")
async def admin_bookings(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    pending = await get_all_bookings(session, status=BookingStatus.PENDING, limit=10)
    if not pending:
        recent = await get_all_bookings(session, limit=5)
        if not recent:
            await message.answer("Бронирований пока нет.")
            return
        text = "📅 **Последние бронирования:**\n\n" + "\n\n".join(format_booking(b) for b in recent)
        await message.answer(text, parse_mode="Markdown")
        return

    lines = []
    for b in pending:
        guest = b.guest_name or (b.user.first_name if b.user else "—")
        lines.append(f"{format_booking(b)}\n👤 {guest}")
    await message.answer(
        "📅 **Ожидают подтверждения:**\n\n" + "\n\n".join(lines),
        parse_mode="Markdown",
        reply_markup=admin_bookings_keyboard(pending),
    )


@router.callback_query(F.data.startswith("abook:confirm:"))
async def admin_confirm_booking(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    booking_id = int(callback.data.split(":")[2])
    booking = await get_booking(session, booking_id)
    if not booking or booking.status != BookingStatus.PENDING:
        await callback.answer("Бронирование недоступно", show_alert=True)
        return
    await confirm_booking(session, booking)
    booking = await get_booking(session, booking_id)
    await callback.message.edit_text(
        f"✅ Бронирование #{booking_id} подтверждено.\n\n{format_booking(booking)}",
        parse_mode="Markdown",
    )
    await callback.answer()
    if booking.user:
        await notify_user_booking_confirmed(callback.bot, booking, booking.user.telegram_id)
    if booking.room.tvil_object_id:
        await notify_admins_tvil_export(callback.bot, booking)


@router.callback_query(F.data.startswith("abook:reject:"))
async def admin_reject_booking(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    booking_id = int(callback.data.split(":")[2])
    booking = await get_booking(session, booking_id)
    if not booking or booking.status != BookingStatus.PENDING:
        await callback.answer("Бронирование недоступно", show_alert=True)
        return
    await cancel_booking(session, booking)
    await callback.message.edit_text(f"❌ Бронирование #{booking_id} отклонено.")
    await callback.answer()
    if booking.user:
        await notify_user_booking_rejected(callback.bot, booking, booking.user.telegram_id)
