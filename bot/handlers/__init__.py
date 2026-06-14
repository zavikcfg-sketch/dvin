from aiogram import Router

from bot.handlers import admin, booking, booking_admin, config, start, subscription


def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(booking.router)
    router.include_router(booking_admin.router)
    router.include_router(config.router)
    router.include_router(subscription.router)
    router.include_router(admin.router)
    return router
