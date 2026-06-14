import secrets
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import async_session, get_session, init_db
from core.models import ServerStatus, Subscription, SubscriptionStatus, User, VpnServer

settings = get_settings()
app = FastAPI(title="VPN Bot Admin", docs_url="/api/docs")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "admin" / "templates"))

# Simple session store (use Redis in production)
_sessions: set[str] = set()


class TvilBlockPayload(BaseModel):
    check_in: str = Field(description="YYYY-MM-DD")
    check_out: str = Field(description="YYYY-MM-DD")


class TvilSyncPayload(BaseModel):
    secret: str
    room_id: int
    blocks: list[TvilBlockPayload]


def _check_tvil_secret(secret: str) -> None:
    if not settings.tvil_webhook_secret or secret != settings.tvil_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")


def require_auth(request: Request) -> None:
    token = request.cookies.get("admin_session")
    if not token or token not in _sessions:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/admin/login")
async def login(request: Request, username: str = Form(), password: str = Form()) -> RedirectResponse:
    if username == settings.admin_username and password == settings.admin_password:
        token = secrets.token_hex(32)
        _sessions.add(token)
        response = RedirectResponse("/admin/dashboard", status_code=303)
        response.set_cookie("admin_session", token, httponly=True)
        return response
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Неверный логин или пароль"}, status_code=401
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    require_auth(request)
    users_count = await session.scalar(select(func.count(User.id)))
    active_subs = await session.scalar(
        select(func.count(Subscription.id)).where(
            Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
        )
    )
    servers = (await session.execute(select(VpnServer))).scalars().all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "users_count": users_count,
            "active_subs": active_subs,
            "servers": servers,
        },
    )


@app.get("/admin/servers", response_class=HTMLResponse)
async def servers_page(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    require_auth(request)
    servers = (await session.execute(select(VpnServer))).scalars().all()
    return templates.TemplateResponse("servers.html", {"request": request, "servers": servers})


@app.post("/admin/servers/add")
async def add_server(
    request: Request,
    name: str = Form(),
    host: str = Form(),
    port: int = Form(443),
    country: str = Form("NL"),
    public_key: str = Form(),
    short_id: str = Form(),
    sni: str = Form("www.microsoft.com"),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    require_auth(request)
    server = VpnServer(
        name=name,
        host=host,
        port=port,
        country=country,
        public_key=public_key,
        short_id=short_id,
        sni=sni,
        status=ServerStatus.ONLINE,
    )
    session.add(server)
    await session.commit()
    return RedirectResponse("/admin/servers", status_code=303)


@app.get("/admin/users", response_class=HTMLResponse)
async def users_page(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    require_auth(request)
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(User).options(selectinload(User.subscription)).order_by(User.created_at.desc()).limit(100)
    )
    users = result.scalars().all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/webhooks/tvil/blocks")
async def tvil_import_blocks(payload: TvilSyncPayload, session: AsyncSession = Depends(get_session)) -> dict:
    from core.tvil_service import import_tvil_blocks_payload

    _check_tvil_secret(payload.secret)
    count = await import_tvil_blocks_payload(
        session,
        payload.room_id,
        [b.model_dump() for b in payload.blocks],
    )
    return {"ok": True, "imported": count}


@app.get("/api/tvil/pending")
async def tvil_pending_exports(secret: str, session: AsyncSession = Depends(get_session)) -> dict:
    from core.tvil_service import get_pending_tvil_exports

    _check_tvil_secret(secret)
    bookings = await get_pending_tvil_exports(session)
    return {
        "items": [
            {
                "booking_id": b.id,
                "room_id": b.room_id,
                "room_name": b.room.name,
                "tvil_object_id": b.room.tvil_object_id,
                "check_in": b.check_in.isoformat(),
                "check_out": b.check_out.isoformat(),
                "guest_name": b.guest_name,
                "status": b.status.value,
            }
            for b in bookings
        ]
    }


@app.post("/api/tvil/exported/{booking_id}")
async def tvil_mark_exported(
    booking_id: int,
    secret: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from core.booking_services import get_booking
    from core.tvil_service import mark_tvil_exported

    _check_tvil_secret(secret)
    booking = await get_booking(session, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    await mark_tvil_exported(session, booking)
    return {"ok": True}
