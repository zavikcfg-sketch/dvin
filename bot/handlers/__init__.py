from aiogram import Router

from bot.handlers import admin, booking, booking_admin, start


def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(booking.router)
    router.include_router(booking_admin.router)
    router.include_router(admin.router)
    return router
