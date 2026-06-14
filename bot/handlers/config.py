import io

import qrcode
from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.keyboards import config_actions_keyboard, servers_keyboard
from core.models import ServerStatus, VpnKey, VpnServer
from core.services import (
    create_vpn_key,
    get_active_subscription,
    get_best_server,
    get_or_create_user,
    get_user_keys,
)
from xray.generator import build_vless_reality_link, build_xray_client_config, config_to_json

router = Router()


@router.message(F.text == "🔑 Мой VPN")
async def my_vpn(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    sub = await get_active_subscription(session, user)
    if not sub:
        await message.answer("❌ Подписка истекла. Перейдите в 💳 Тарифы для продления.")
        return

    keys = await get_user_keys(session, user)
    if keys:
        key = keys[0]
        link = build_vless_reality_link(key, key.server)
        await message.answer(
            f"✅ Ваш VPN-ключ ({key.server.name}):\n\n"
            f"`{link}`\n\n"
            "Нажмите на ссылку, чтобы скопировать.",
            parse_mode="Markdown",
            reply_markup=config_actions_keyboard(key.id),
        )
        return

    result = await session.execute(
        select(VpnServer).where(VpnServer.status == ServerStatus.ONLINE).order_by(VpnServer.current_users)
    )
    servers = list(result.scalars().all())
    if not servers:
        await message.answer("⚠️ Серверы временно недоступны. Попробуйте позже.")
        return

    if len(servers) == 1:
        key = await create_vpn_key(session, user, servers[0])
        link = build_vless_reality_link(key, servers[0])
        await message.answer(
            f"✅ Ключ создан ({servers[0].name}):\n\n`{link}`",
            parse_mode="Markdown",
            reply_markup=config_actions_keyboard(key.id),
        )
        return

    await message.answer("Выберите сервер:", reply_markup=servers_keyboard(servers))


@router.callback_query(F.data.startswith("server:"))
async def select_server(callback: CallbackQuery, session: AsyncSession) -> None:
    server_id = int(callback.data.split(":")[1])
    user = await get_or_create_user(session, callback.from_user.id)
    sub = await get_active_subscription(session, user)
    if not sub:
        await callback.answer("Подписка истекла", show_alert=True)
        return

    result = await session.execute(select(VpnServer).where(VpnServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        await callback.answer("Сервер не найден", show_alert=True)
        return

    key = await create_vpn_key(session, user, server)
    link = build_vless_reality_link(key, server)
    await callback.message.edit_text(
        f"✅ Ключ создан ({server.name}):\n\n`{link}`",
        parse_mode="Markdown",
        reply_markup=config_actions_keyboard(key.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qr:"))
async def send_qr(callback: CallbackQuery, session: AsyncSession) -> None:
    key_id = int(callback.data.split(":")[1])
    key = await _get_key(session, key_id, callback.from_user.id)
    if not key:
        await callback.answer("Ключ не найден", show_alert=True)
        return

    link = build_vless_reality_link(key, key.server)
    img = qrcode.make(link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="vpn-qr.png"),
        caption="Отсканируйте QR-код в Hiddify или v2rayN",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("json:"))
async def send_json(callback: CallbackQuery, session: AsyncSession) -> None:
    key_id = int(callback.data.split(":")[1])
    key = await _get_key(session, key_id, callback.from_user.id)
    if not key:
        await callback.answer("Ключ не найден", show_alert=True)
        return

    config = build_xray_client_config(key, key.server)
    content = config_to_json(config).encode()
    await callback.message.answer_document(
        BufferedInputFile(content, filename="xray-config.json"),
        caption="Импортируйте этот файл в v2rayN",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("copy:"))
async def copy_hint(callback: CallbackQuery, session: AsyncSession) -> None:
    key_id = int(callback.data.split(":")[1])
    key = await _get_key(session, key_id, callback.from_user.id)
    if not key:
        await callback.answer("Ключ не найден", show_alert=True)
        return
    link = build_vless_reality_link(key, key.server)
    await callback.answer("Ссылка в сообщении выше — нажмите и удерживайте для копирования")
    await callback.message.answer(f"`{link}`", parse_mode="Markdown")


@router.message(F.text == "📊 Статус")
async def status(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    sub = user.subscription
    if not sub:
        await message.answer("Подписка не найдена. Нажмите /start")
        return

    status_emoji = {"trial": "🎁", "active": "✅", "expired": "❌", "blocked": "🚫"}
    from core.services import format_expires, format_traffic

    await message.answer(
        f"{status_emoji.get(sub.status.value, '❓')} **Статус:** {sub.status.value}\n"
        f"📅 **До:** {format_expires(sub.expires_at)}\n"
        f"📶 **Трафик:** {format_traffic(sub.traffic_used_bytes, sub.traffic_limit_gb)}",
        parse_mode="Markdown",
    )


async def _get_key(session: AsyncSession, key_id: int, telegram_id: int) -> VpnKey | None:
    result = await session.execute(
        select(VpnKey)
        .options(selectinload(VpnKey.server), selectinload(VpnKey.user))
        .where(VpnKey.id == key_id)
    )
    key = result.scalar_one_or_none()
    if not key or key.user.telegram_id != telegram_id:
        return None
    return key
