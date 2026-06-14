from datetime import date, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.calendar_keyboard import build_calendar
from bot.keyboards import (
    booking_confirm_keyboard,
    booking_menu,
    rooms_keyboard,
    user_bookings_keyboard,
)
from bot.states import BookingStates
from core.booking_services import (
    create_booking,
    format_booking,
    get_active_rooms,
    get_availability_summary,
    get_blocked_dates,
    get_booking,
    get_room,
    get_user_bookings,
    is_room_available,
    cancel_booking,
)
from core.models import BookingStatus
from core.services import get_or_create_user

router = Router()


@router.message(F.text == "🏨 Бронирование")
async def booking_entry(message: Message) -> None:
    await message.answer(
        "🏨 **Бронирование номеров (посуточно)**\n\n"
        "📅 **Забронировать** — выбор комнаты и дат заезда/выезда\n"
        "🗓 **Свободные даты** — календарь доступности\n"
        "📋 **Мои брони** — ваши заявки и отмена",
        parse_mode="Markdown",
        reply_markup=booking_menu(),
    )


@router.message(F.text == "📅 Забронировать")
async def start_booking(message: Message, session: AsyncSession, state: FSMContext) -> None:
    rooms = await get_active_rooms(session)
    if not rooms:
        await message.answer(
            "Комнаты пока не добавлены. Обратитесь к администратору.",
            reply_markup=booking_menu(),
        )
        return
    await state.set_state(BookingStates.choosing_room)
    await message.answer(
        "Выберите комнату:",
        reply_markup=rooms_keyboard(rooms, prefix="bookroom"),
    )


@router.callback_query(F.data.startswith("bookroom:"))
async def select_room(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    if callback.data == "bookroom:cancel":
        await state.clear()
        await callback.message.edit_text("Бронирование отменено.")
        await callback.answer()
        return

    room_id = int(callback.data.split(":")[1])
    room = await get_room(session, room_id)
    if not room or not room.is_active:
        await callback.answer("Комната недоступна", show_alert=True)
        return

    today = date.today()
    blocked = await get_blocked_dates(session, room_id, today, today + timedelta(days=365))
    await state.update_data(room_id=room_id, room_name=room.name, price=room.price_per_night)
    await state.set_state(BookingStates.choosing_check_in)
    tvil_line = ""
    if room.tvil_listing_url:
        tvil_line = f"\n🌐 [Объявление на TVIL]({room.tvil_listing_url})"
    await callback.message.edit_text(
        f"🏠 **{room.name}**{tvil_line}\n\nВыберите дату **заезда**:",
        parse_mode="Markdown",
        reply_markup=build_calendar(
            today.year,
            today.month,
            prefix="cin",
            min_date=today,
            blocked_dates=blocked,
        ),
    )
    await callback.answer()


async def _handle_calendar_nav(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    *,
    prefix: str,
    mode: str,
) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    if action == "noop":
        await callback.answer()
        return
    if action == "cancel":
        await state.clear()
        await callback.message.edit_text("Бронирование отменено.")
        await callback.answer()
        return

    data = await state.get_data()
    room_id = data["room_id"]
    today = date.today()
    blocked = await get_blocked_dates(session, room_id, today, today + timedelta(days=365))

    if action == "nav":
        year, month = map(int, parts[2].split("-"))
        min_date = today if mode == "check_in" else date.fromisoformat(data["check_in"]) + timedelta(days=1)
        selected = date.fromisoformat(data["check_in"]) if mode == "check_out" and "check_in" in data else None
        await callback.message.edit_reply_markup(
            reply_markup=build_calendar(
                year,
                month,
                prefix=prefix,
                min_date=min_date,
                blocked_dates=blocked if mode == "check_in" else blocked,
                selected=selected,
            )
        )
        await callback.answer()
        return

    if action == "pick":
        picked = date.fromisoformat(parts[2])
        if mode == "check_in":
            await state.update_data(check_in=picked.isoformat())
            await state.set_state(BookingStates.choosing_check_out)
            min_out = picked + timedelta(days=1)
            await callback.message.edit_text(
                f"Заезд: **{picked.strftime('%d.%m.%Y')}**\n\nВыберите дату **выезда**:",
                parse_mode="Markdown",
                reply_markup=build_calendar(
                    min_out.year,
                    min_out.month,
                    prefix="cout",
                    min_date=min_out,
                    blocked_dates=blocked,
                ),
            )
        else:
            check_in = date.fromisoformat(data["check_in"])
            check_out = picked
            if check_out <= check_in:
                await callback.answer("Дата выезда должна быть позже заезда", show_alert=True)
                return
            available = await is_room_available(session, room_id, check_in, check_out)
            if not available:
                await callback.answer("На эти даты комната занята", show_alert=True)
                return
            nights = (check_out - check_in).days
            price = data.get("price", 0)
            total = price * nights
            await state.update_data(check_out=check_out.isoformat(), nights=nights, total=total)
            await state.set_state(BookingStates.confirming)
            price_text = f"\n💰 **{price}₽/ночь × {nights} = {total}₽**" if price else ""
            await callback.message.edit_text(
                f"🏠 **{data['room_name']}**\n"
                f"📅 Заезд: **{check_in.strftime('%d.%m.%Y')}**\n"
                f"📅 Выезд: **{check_out.strftime('%d.%m.%Y')}**\n"
                f"🌙 Ночей: **{nights}**{price_text}\n\n"
                "Подтвердить бронирование?",
                parse_mode="Markdown",
                reply_markup=booking_confirm_keyboard(),
            )
        await callback.answer()


@router.callback_query(BookingStates.choosing_check_in, F.data.startswith("cin:"))
async def calendar_check_in(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await _handle_calendar_nav(callback, session, state, prefix="cin", mode="check_in")


@router.callback_query(BookingStates.choosing_check_out, F.data.startswith("cout:"))
async def calendar_check_out(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await _handle_calendar_nav(callback, session, state, prefix="cout", mode="check_out")


@router.callback_query(BookingStates.confirming, F.data == "book:cancel")
async def cancel_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Бронирование отменено.")
    await callback.answer()


@router.callback_query(BookingStates.confirming, F.data == "book:confirm")
async def confirm_booking(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    user = await get_or_create_user(
        session,
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
    )
    room = await get_room(session, data["room_id"])
    if not room:
        await callback.answer("Комната не найдена", show_alert=True)
        await state.clear()
        return

    check_in = date.fromisoformat(data["check_in"])
    check_out = date.fromisoformat(data["check_out"])
    if not await is_room_available(session, room.id, check_in, check_out):
        await callback.answer("Комната уже занята на эти даты", show_alert=True)
        return

    guest_name = callback.from_user.full_name or callback.from_user.first_name
    booking = await create_booking(
        session,
        user,
        room,
        check_in,
        check_out,
        guest_name=guest_name,
    )
    booking = await get_booking(session, booking.id)
    await state.clear()
    tvil_note = ""
    if room.tvil_listing_url:
        from core.tvil_service import build_tvil_listing_url

        tvil_url = build_tvil_listing_url(room, check_in, check_out)
        tvil_note = f"\n\n🌐 [Забронировать на TVIL]({tvil_url})"
    await callback.message.edit_text(
        f"✅ Заявка создана!\n\n{format_booking(booking)}\n\n"
        "Ожидайте подтверждения администратора." + tvil_note,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
    await callback.answer()

    from bot.notifications import notify_admins_new_booking

    await notify_admins_new_booking(callback.bot, booking)


@router.message(F.text == "🗓 Свободные даты")
async def show_availability_start(message: Message, session: AsyncSession) -> None:
    rooms = await get_active_rooms(session)
    if not rooms:
        await message.answer("Комнаты пока не добавлены.", reply_markup=booking_menu())
        return
    await message.answer("Выберите комнату:", reply_markup=rooms_keyboard(rooms, prefix="avail"))


@router.callback_query(F.data.startswith("avail:"))
async def show_availability(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data == "avail:cancel":
        await callback.message.delete()
        await callback.answer()
        return

    room_id = int(callback.data.split(":")[1])
    room = await get_room(session, room_id)
    if not room:
        await callback.answer("Комната не найдена", show_alert=True)
        return

    today = date.today()
    summary = await get_availability_summary(session, room_id, today, days=30)
    lines = [f"🗓 **{room.name}** — ближайшие 30 дней:\n"]
    for day, free in summary:
        mark = "🟢" if free else "🔴"
        lines.append(f"{mark} {day.strftime('%d.%m.%Y (%a)')}")

    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown")
    await callback.answer()


@router.message(F.text == "📋 Мои брони")
async def my_bookings(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(
        session,
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )
    bookings = await get_user_bookings(session, user)
    active = [b for b in bookings if b.status != BookingStatus.CANCELLED]
    if not active:
        await message.answer("У вас нет активных бронирований.", reply_markup=booking_menu())
        return

    text = "📋 **Ваши бронирования:**\n\n" + "\n\n".join(format_booking(b) for b in active)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=user_bookings_keyboard(active),
    )


@router.callback_query(F.data.startswith("ubook:cancel:"))
async def cancel_user_booking(callback: CallbackQuery, session: AsyncSession) -> None:
    booking_id = int(callback.data.split(":")[2])
    booking = await get_booking(session, booking_id)
    if not booking or booking.user.telegram_id != callback.from_user.id:
        await callback.answer("Бронирование не найдено", show_alert=True)
        return
    if booking.status == BookingStatus.CANCELLED:
        await callback.answer("Уже отменено", show_alert=True)
        return

    await cancel_booking(session, booking)
    await callback.message.edit_text(
        f"❌ Бронирование #{booking_id} отменено.",
    )
    await callback.answer()
