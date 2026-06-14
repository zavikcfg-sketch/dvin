import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bookings: Mapped[list["RoomBooking"]] = relationship(back_populates="user")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_per_night: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tvil_listing_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tvil_object_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tvil_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bookings: Mapped[list["RoomBooking"]] = relationship(back_populates="room")
    external_blocks: Mapped[list["ExternalCalendarBlock"]] = relationship(back_populates="room")


class ExternalCalendarBlock(Base):
    __tablename__ = "external_calendar_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(32), default="tvil")
    external_uid: Mapped[str | None] = mapped_column(String(256), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(256), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    room: Mapped["Room"] = relationship(back_populates="external_blocks")


class RoomBooking(Base):
    __tablename__ = "room_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.PENDING)
    guest_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    guest_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nights: Mapped[int] = mapped_column(Integer)
    total_price: Mapped[int] = mapped_column(Integer, default=0)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    tvil_exported: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="bookings")
    room: Mapped["Room"] = relationship(back_populates="bookings")
