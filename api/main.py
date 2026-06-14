from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import get_session, init_db

settings = get_settings()
app = FastAPI(title="TVIL Booking Bot API", docs_url="/api/docs")


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


@app.on_event("startup")
async def startup() -> None:
    await init_db()


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
