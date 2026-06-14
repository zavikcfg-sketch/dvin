from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from core.booking_services import format_booking
from core.config import get_settings
from core.models import RoomBooking

settings = get_settings()


async def notify_admins_new_booking(bot: Bot, booking: RoomBooking) -> None:
    text = (
        "🔔 **Новая заявка на бронирование**\n\n"
        f"{format_booking(booking)}\n"
        f"👤 {booking.guest_name or '—'}"
    )
    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception:
            pass


async def notify_admins_tvil_export(bot: Bot, booking: RoomBooking) -> None:
    from core.tvil_service import format_tvil_close_hint

    text = format_tvil_close_hint(booking) + f"\n\nПосле закрытия: `/tvil_done {booking.id}`"
    for admin_id in settings.admin_id_list:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            pass


async def notify_user_booking_confirmed(bot: Bot, booking: RoomBooking, telegram_id: int) -> None:
    await bot.send_message(
        telegram_id,
        f"✅ Ваше бронирование подтверждено!\n\n{format_booking(booking)}",
        parse_mode="Markdown",
    )


async def notify_user_booking_rejected(bot: Bot, booking: RoomBooking, telegram_id: int) -> None:
    await bot.send_message(
        telegram_id,
        f"❌ Бронирование #{booking.id} отклонено администратором.",
    )


async def send_checkin_reminders(bot: Bot, session: AsyncSession) -> None:
    from datetime import date, timedelta

    from core.booking_services import get_upcoming_checkins, mark_reminder_sent

    tomorrow = date.today() + timedelta(days=1)
    bookings = await get_upcoming_checkins(session, tomorrow)
    for booking in bookings:
        if not booking.user:
            continue
        try:
            await bot.send_message(
                booking.user.telegram_id,
                f"⏰ Напоминание: завтра заезд!\n\n{format_booking(booking)}",
                parse_mode="Markdown",
            )
            await mark_reminder_sent(session, booking)
        except Exception:
            pass
