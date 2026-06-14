import logging
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.models import BookingStatus, ExternalCalendarBlock, Room, RoomBooking

logger = logging.getLogger(__name__)

SOURCE_TVIL = "tvil"
DATE_RANGE_RE = re.compile(
    r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})\s*[-–—]\s*(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})"
)


def _parse_date(day: str, month: str, year: str) -> date:
    y = int(year)
    if y < 100:
        y += 2000
    return date(y, int(month), int(day))


def parse_busy_periods(text: str) -> list[tuple[date, date]]:
    periods: list[tuple[date, date]] = []
    for match in DATE_RANGE_RE.finditer(text):
        check_in = _parse_date(match.group(1), match.group(2), match.group(3))
        check_out = _parse_date(match.group(4), match.group(5), match.group(6))
        if check_out > check_in:
            periods.append((check_in, check_out))
    return periods


async def replace_tvil_blocks(
    session: AsyncSession,
    room: Room,
    periods: list[tuple[date, date]],
) -> int:
    now = datetime.now(timezone.utc)
    await session.execute(
        delete(ExternalCalendarBlock).where(
            ExternalCalendarBlock.room_id == room.id,
            ExternalCalendarBlock.source == SOURCE_TVIL,
        )
    )
    for check_in, check_out in periods:
        session.add(
            ExternalCalendarBlock(
                room_id=room.id,
                check_in=check_in,
                check_out=check_out,
                source=SOURCE_TVIL,
                synced_at=now,
            )
        )
    room.tvil_last_sync_at = now
    await session.commit()
    return len(periods)


async def import_tvil_blocks_text(session: AsyncSession, room: Room, text: str) -> int:
    periods = parse_busy_periods(text)
    if not periods:
        raise ValueError("Не найдено периодов. Формат: 14.06.2025-16.06.2025")
    return await replace_tvil_blocks(session, room, periods)


async def import_tvil_blocks_payload(
    session: AsyncSession,
    room_id: int,
    blocks: list[dict],
) -> int:
    room = await session.get(Room, room_id)
    if not room:
        raise ValueError(f"Комната #{room_id} не найдена")

    periods: list[tuple[date, date]] = []
    for block in blocks:
        check_in = date.fromisoformat(str(block["check_in"]))
        check_out = date.fromisoformat(str(block["check_out"]))
        if check_out > check_in:
            periods.append((check_in, check_out))
    if not periods:
        raise ValueError("Список блоков пуст")
    return await replace_tvil_blocks(session, room, periods)


async def get_pending_tvil_exports(session: AsyncSession) -> list[RoomBooking]:
    result = await session.execute(
        select(RoomBooking)
        .options(selectinload(RoomBooking.room))
        .join(Room)
        .where(
            RoomBooking.status.in_((BookingStatus.PENDING, BookingStatus.CONFIRMED)),
            RoomBooking.tvil_exported.is_(False),
            Room.tvil_object_id.is_not(None),
            Room.tvil_object_id != "",
        )
        .order_by(RoomBooking.check_in)
    )
    return list(result.scalars().all())


async def mark_tvil_exported(session: AsyncSession, booking: RoomBooking) -> None:
    booking.tvil_exported = True
    await session.commit()


def build_tvil_owner_calendar_url() -> str:
    return "https://lk.tvil.ru/"


def build_tvil_listing_url(room: Room, check_in: date | None = None, check_out: date | None = None) -> str | None:
    if not room.tvil_listing_url:
        return None
    url = room.tvil_listing_url.rstrip("/")
    if check_in and check_out:
        return (
            f"{url}?date_from={check_in.strftime('%d.%m.%Y')}"
            f"&date_to={check_out.strftime('%d.%m.%Y')}"
        )
    return url


def format_tvil_close_hint(booking: RoomBooking) -> str:
    last_night = booking.check_out - timedelta(days=1)
    return (
        f"📌 **Закройте даты на TVIL** (объект `{booking.room.tvil_object_id or '—'}`)\n"
        f"Заезд: **{booking.check_in.strftime('%d.%m.%Y')}**\n"
        f"Выезд: **{booking.check_out.strftime('%d.%m.%Y')}**\n"
        f"Закрыть в календаре до **{last_night.strftime('%d.%m.%Y')}** включительно\n"
        f"🔗 {build_tvil_owner_calendar_url()}"
    )
