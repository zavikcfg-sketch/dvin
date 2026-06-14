from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def _sqlite_column_names(connection, table: str) -> set[str]:
    rows = connection.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _migrate_schema_sync(connection) -> None:
    if connection.dialect.name != "sqlite":
        return

    room_columns = _sqlite_column_names(connection, "rooms")
    room_additions = {
        "tvil_listing_url": "VARCHAR(512)",
        "tvil_object_id": "VARCHAR(64)",
        "tvil_last_sync_at": "DATETIME",
    }
    for column, col_type in room_additions.items():
        if column not in room_columns:
            connection.exec_driver_sql(f"ALTER TABLE rooms ADD COLUMN {column} {col_type}")

    booking_columns = _sqlite_column_names(connection, "room_bookings")
    if "tvil_exported" not in booking_columns:
        connection.exec_driver_sql("ALTER TABLE room_bookings ADD COLUMN tvil_exported BOOLEAN DEFAULT 0")


async def init_db() -> None:
    from core import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_schema_sync)
