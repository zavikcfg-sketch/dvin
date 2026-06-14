from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from core.models import BookingStatus, Room, RoomBooking, VpnServer


def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row("🔑 Мой VPN", "📊 Статус")
    builder.row("💳 Тарифы", "🏨 Бронирование")
    builder.row("❓ Помощь")
    return builder.as_markup(resize_keyboard=True)


def booking_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row("📅 Забронировать", "🗓 Свободные даты")
    builder.row("📋 Мои брони", "◀️ Главное меню")
    return builder.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row("👥 Пользователи", "🖥 Серверы")
    builder.row("🏠 Комнаты", "📅 Брони")
    builder.row("📢 Рассылка", "📈 Статистика")
    builder.row("◀️ Главное меню")
    return builder.as_markup(resize_keyboard=True)


def plans_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 мес — 199₽", callback_data="plan:30:199"),
        InlineKeyboardButton(text="3 мес — 499₽", callback_data="plan:90:499"),
    )
    builder.row(
        InlineKeyboardButton(text="6 мес — 899₽", callback_data="plan:180:899"),
        InlineKeyboardButton(text="12 мес — 1499₽", callback_data="plan:365:1499"),
    )
    builder.row(InlineKeyboardButton(text="🎁 Пробный период", callback_data="plan:trial"))
    return builder.as_markup()


def servers_keyboard(servers: list[VpnServer]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in servers:
        flag = _country_flag(s.country)
        builder.row(
            InlineKeyboardButton(
                text=f"{flag} {s.name} ({s.current_users}/{s.max_users})",
                callback_data=f"server:{s.id}",
            )
        )
    return builder.as_markup()


def config_actions_keyboard(key_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy:{key_id}"),
        InlineKeyboardButton(text="📱 QR-код", callback_data=f"qr:{key_id}"),
    )
    builder.row(InlineKeyboardButton(text="📄 JSON-конфиг", callback_data=f"json:{key_id}"))
    return builder.as_markup()


def _country_flag(code: str) -> str:
    code = code.upper()
    if len(code) != 2:
        return "🌐"
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


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
