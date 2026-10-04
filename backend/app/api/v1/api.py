from fastapi import APIRouter

from app.api.v1.endpoints import (
    alarms,
    assistant,
    calendar,
    context,
    destinations,
    eta,
    health,
    location,
    notifications,
    personalization,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(
    destinations.router, prefix="/destinations", tags=["Destinations"]
)
api_router.include_router(alarms.router, prefix="/alarms", tags=["Alarms"])
api_router.include_router(location.router, tags=["Location & Maps"])
api_router.include_router(eta.router, prefix="/eta", tags=["ETA Engine"])
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"]
)
api_router.include_router(
    context.router, prefix="/context", tags=["Context Intelligence"]
)
api_router.include_router(
    calendar.router, prefix="/calendar", tags=["Calendar"]
)
api_router.include_router(
    assistant.router, prefix="/assistant", tags=["AI Assistant"]
)
api_router.include_router(
    personalization.router, prefix="/personalization", tags=["Personalization"]
)

