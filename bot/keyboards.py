from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from core.models import BookingStatus, Room, RoomBooking


def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📅 Забронировать"), KeyboardButton(text="🗓 Свободные даты"))
    builder.row(KeyboardButton(text="📋 Мои брони"), KeyboardButton(text="❓ Помощь"))
    return builder.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🏠 Комнаты"), KeyboardButton(text="📅 Брони"))
    builder.row(KeyboardButton(text="📈 Статистика"), KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)


def rooms_keyboard(rooms: list[Room], *, prefix: str = "room") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for room in rooms:
        price = f" — {room.price_per_night}₽/ночь" if room.price_per_night else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{room.name}{price}",
                callback_data=f"{prefix}:{room.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"{prefix}:cancel"))
    return builder.as_markup()


def booking_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="book:confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="book:cancel"),
    )
    return builder.as_markup()


def user_bookings_keyboard(bookings: list[RoomBooking]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        if booking.status == BookingStatus.CANCELLED:
            continue
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Отменить #{booking.id} ({booking.room.name})",
                callback_data=f"ubook:cancel:{booking.id}",
            )
        )
    return builder.as_markup()


def admin_bookings_keyboard(bookings: list[RoomBooking]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        if booking.status != BookingStatus.PENDING:
            continue
        builder.row(
            InlineKeyboardButton(
                text=f"✅ #{booking.id} {booking.room.name}",
                callback_data=f"abook:confirm:{booking.id}",
            ),
            InlineKeyboardButton(
                text="❌",
                callback_data=f"abook:reject:{booking.id}",
            ),
        )
    return builder.as_markup()


def admin_rooms_keyboard(rooms: list[Room]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for room in rooms:
        status = "🟢" if room.is_active else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {room.name}",
                callback_data=f"aroom:toggle:{room.id}",
            )
        )
    return builder.as_markup()
