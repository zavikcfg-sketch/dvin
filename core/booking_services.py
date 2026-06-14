from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import BookingStatus, ExternalCalendarBlock, Room, RoomBooking, User

ACTIVE_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)


def nights_between(check_in: date, check_out: date) -> int:
    return (check_out - check_in).days


async def get_active_rooms(session: AsyncSession) -> list[Room]:
    result = await session.execute(
        select(Room).where(Room.is_active.is_(True)).order_by(Room.name)
    )
    return list(result.scalars().all())


async def get_room(session: AsyncSession, room_id: int) -> Room | None:
    return await session.get(Room, room_id)


async def get_external_blocks_in_range(
    session: AsyncSession,
    room_id: int,
    start: date,
    end: date,
) -> list[ExternalCalendarBlock]:
    result = await session.execute(
        select(ExternalCalendarBlock)
        .where(
            ExternalCalendarBlock.room_id == room_id,
            ExternalCalendarBlock.check_in < end,
            ExternalCalendarBlock.check_out > start,
        )
        .order_by(ExternalCalendarBlock.check_in)
    )
    return list(result.scalars().all())


async def get_room_bookings_in_range(
    session: AsyncSession,
    room_id: int,
    start: date,
    end: date,
    *,
    exclude_booking_id: int | None = None,
) -> list[RoomBooking]:
    query = (
        select(RoomBooking)
        .where(
            RoomBooking.room_id == room_id,
            RoomBooking.status.in_(ACTIVE_STATUSES),
            RoomBooking.check_in < end,
            RoomBooking.check_out > start,
        )
        .order_by(RoomBooking.check_in)
    )
    if exclude_booking_id:
        query = query.where(RoomBooking.id != exclude_booking_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def is_room_available(
    session: AsyncSession,
    room_id: int,
    check_in: date,
    check_out: date,
    *,
    exclude_booking_id: int | None = None,
) -> bool:
    if check_out <= check_in:
        return False
    bookings = await get_room_bookings_in_range(
        session, room_id, check_in, check_out, exclude_booking_id=exclude_booking_id
    )
    if bookings:
        return False
    external = await get_external_blocks_in_range(session, room_id, check_in, check_out)
    return len(external) == 0


def _collect_blocked_days(
    ranges: list[tuple[date, date]],
    start: date,
    end: date,
) -> set[date]:
    blocked: set[date] = set()
    for range_in, range_out in ranges:
        day = range_in
        while day < range_out:
            if start <= day < end:
                blocked.add(day)
            day += timedelta(days=1)
    return blocked


async def get_blocked_dates(
    session: AsyncSession,
    room_id: int,
    start: date,
    end: date,
) -> set[date]:
    bookings = await get_room_bookings_in_range(session, room_id, start, end)
    external = await get_external_blocks_in_range(session, room_id, start, end)
    ranges = [(b.check_in, b.check_out) for b in bookings]
    ranges.extend((b.check_in, b.check_out) for b in external)
    return _collect_blocked_days(ranges, start, end)


async def get_availability_summary(
    session: AsyncSession,
    room_id: int,
    start: date,
    days: int = 30,
) -> list[tuple[date, bool]]:
    end = start + timedelta(days=days)
    blocked = await get_blocked_dates(session, room_id, start, end)
    return [(start + timedelta(days=i), (start + timedelta(days=i)) not in blocked) for i in range(days)]


async def create_booking(
    session: AsyncSession,
    user: User,
    room: Room,
    check_in: date,
    check_out: date,
    guest_name: str | None = None,
    guest_phone: str | None = None,
) -> RoomBooking:
    nights = nights_between(check_in, check_out)
    booking = RoomBooking(
        user_id=user.id,
        room_id=room.id,
        check_in=check_in,
        check_out=check_out,
        nights=nights,
        total_price=room.price_per_night * nights,
        guest_name=guest_name,
        guest_phone=guest_phone,
        status=BookingStatus.PENDING,
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_user_bookings(session: AsyncSession, user: User) -> list[RoomBooking]:
    result = await session.execute(
        select(RoomBooking)
        .options(selectinload(RoomBooking.room))
        .where(RoomBooking.user_id == user.id)
        .order_by(RoomBooking.check_in.desc())
    )
    return list(result.scalars().all())


async def get_booking(session: AsyncSession, booking_id: int) -> RoomBooking | None:
    result = await session.execute(
        select(RoomBooking)
        .options(selectinload(RoomBooking.room), selectinload(RoomBooking.user))
        .where(RoomBooking.id == booking_id)
    )
    return result.scalar_one_or_none()


async def cancel_booking(session: AsyncSession, booking: RoomBooking) -> RoomBooking:
    booking.status = BookingStatus.CANCELLED
    await session.commit()
    await session.refresh(booking)
    return booking


async def confirm_booking(session: AsyncSession, booking: RoomBooking) -> RoomBooking:
    booking.status = BookingStatus.CONFIRMED
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_all_bookings(
    session: AsyncSession,
    *,
    status: BookingStatus | None = None,
    limit: int = 20,
) -> list[RoomBooking]:
    query = (
        select(RoomBooking)
        .options(selectinload(RoomBooking.room), selectinload(RoomBooking.user))
        .order_by(RoomBooking.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(RoomBooking.status == status)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_upcoming_checkins(session: AsyncSession, on_date: date) -> list[RoomBooking]:
    result = await session.execute(
        select(RoomBooking)
        .options(selectinload(RoomBooking.room), selectinload(RoomBooking.user))
        .where(
            RoomBooking.check_in == on_date,
            RoomBooking.status == BookingStatus.CONFIRMED,
            RoomBooking.reminder_sent.is_(False),
        )
    )
    return list(result.scalars().all())


async def mark_reminder_sent(session: AsyncSession, booking: RoomBooking) -> None:
    booking.reminder_sent = True
    await session.commit()


async def add_room(
    session: AsyncSession,
    name: str,
    description: str | None = None,
    price_per_night: int = 0,
) -> Room:
    room = Room(name=name, description=description, price_per_night=price_per_night)
    session.add(room)
    await session.commit()
    await session.refresh(room)
    return room


async def set_room_active(session: AsyncSession, room: Room, is_active: bool) -> Room:
    room.is_active = is_active
    await session.commit()
    await session.refresh(room)
    return room


def format_booking(booking: RoomBooking) -> str:
    status_labels = {
        BookingStatus.PENDING: "⏳ Ожидает подтверждения",
        BookingStatus.CONFIRMED: "✅ Подтверждено",
        BookingStatus.CANCELLED: "❌ Отменено",
    }
    price_line = f"\n💰 Сумма: {booking.total_price}₽" if booking.total_price else ""
    return (
        f"**#{booking.id}** — {booking.room.name}\n"
        f"📅 {booking.check_in.strftime('%d.%m.%Y')} → {booking.check_out.strftime('%d.%m.%Y')}\n"
        f"🌙 Ночей: {booking.nights}{price_line}\n"
        f"{status_labels.get(booking.status, booking.status.value)}"
    )
