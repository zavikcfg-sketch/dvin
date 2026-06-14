import enum
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class SubscriptionStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    subscription: Mapped["Subscription | None"] = relationship(back_populates="user", uselist=False)
    vpn_keys: Mapped[list["VpnKey"]] = relationship(back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL
    )
    traffic_limit_gb: Mapped[int] = mapped_column(Integer, default=50)
    traffic_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="subscription")


class VpnServer(Base):
    __tablename__ = "vpn_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=443)
    status: Mapped[ServerStatus] = mapped_column(Enum(ServerStatus), default=ServerStatus.ONLINE)
    country: Mapped[str] = mapped_column(String(8), default="NL")
    max_users: Mapped[int] = mapped_column(Integer, default=500)
    current_users: Mapped[int] = mapped_column(Integer, default=0)

    # Xray Reality settings
    public_key: Mapped[str] = mapped_column(String(128))
    short_id: Mapped[str] = mapped_column(String(16))
    sni: Mapped[str] = mapped_column(String(255), default="www.microsoft.com")
    fingerprint: Mapped[str] = mapped_column(String(32), default="chrome")

    keys: Mapped[list["VpnKey"]] = relationship(back_populates="server")


class VpnKey(Base):
    __tablename__ = "vpn_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    server_id: Mapped[int] = mapped_column(ForeignKey("vpn_servers.id"))
    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()))
    label: Mapped[str] = mapped_column(String(64), default="default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="vpn_keys")
    server: Mapped["VpnServer"] = relationship(back_populates="keys")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    plan_days: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    provider_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BotMessage(Base):
    __tablename__ = "bot_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


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

    user: Mapped["User"] = relationship()
    room: Mapped["Room"] = relationship(back_populates="bookings")
