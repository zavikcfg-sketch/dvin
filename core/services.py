from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import get_settings
from core.models import ServerStatus, Subscription, SubscriptionStatus, User, VpnKey, VpnServer
from xray.generator import generate_new_uuid


settings = get_settings()


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str | None = None,
) -> User:
    result = await session.execute(
        select(User).options(selectinload(User.subscription)).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user:
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        return user

    user = User(telegram_id=telegram_id, username=username, first_name=first_name)
    session.add(user)
    await session.flush()

    expires = datetime.now(timezone.utc) + timedelta(days=settings.trial_days)
    subscription = Subscription(
        user_id=user.id,
        status=SubscriptionStatus.TRIAL,
        traffic_limit_gb=settings.default_traffic_gb,
        expires_at=expires,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(user)
    return user


async def get_active_subscription(session: AsyncSession, user: User) -> Subscription | None:
    if not user.subscription:
        return None
    sub = user.subscription
    now = datetime.now(timezone.utc)
    if sub.expires_at.replace(tzinfo=timezone.utc) < now and sub.status != SubscriptionStatus.BLOCKED:
        sub.status = SubscriptionStatus.EXPIRED
        await session.commit()
    if sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL):
        return sub
    return None


async def get_best_server(session: AsyncSession) -> VpnServer | None:
    result = await session.execute(
        select(VpnServer)
        .where(VpnServer.status == ServerStatus.ONLINE)
        .order_by(VpnServer.current_users.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_vpn_key(session: AsyncSession, user: User, server: VpnServer) -> VpnKey:
    key = VpnKey(user_id=user.id, server_id=server.id, uuid=generate_new_uuid())
    session.add(key)
    server.current_users += 1
    await session.commit()
    await session.refresh(key)
    return key


async def get_user_keys(session: AsyncSession, user: User) -> list[VpnKey]:
    result = await session.execute(
        select(VpnKey)
        .options(selectinload(VpnKey.server))
        .where(VpnKey.user_id == user.id, VpnKey.is_active.is_(True))
    )
    return list(result.scalars().all())


async def extend_subscription(
    session: AsyncSession, user: User, days: int, traffic_gb: int | None = None
) -> Subscription:
    sub = user.subscription
    now = datetime.now(timezone.utc)
    if sub.expires_at.replace(tzinfo=timezone.utc) < now:
        sub.expires_at = now + timedelta(days=days)
    else:
        sub.expires_at = sub.expires_at.replace(tzinfo=timezone.utc) + timedelta(days=days)
    sub.status = SubscriptionStatus.ACTIVE
    if traffic_gb:
        sub.traffic_limit_gb = traffic_gb
    await session.commit()
    return sub


def format_traffic(bytes_used: int, limit_gb: int) -> str:
    used_gb = bytes_used / (1024**3)
    return f"{used_gb:.2f} / {limit_gb} ГБ"


def format_expires(expires_at: datetime) -> str:
    return expires_at.strftime("%d.%m.%Y %H:%M UTC")
