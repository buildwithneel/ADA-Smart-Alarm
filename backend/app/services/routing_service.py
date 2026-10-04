from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.config import settings
from app.core.errors import ValidationException
from app.core.redis import get_redis_client
from app.integrations.maps.factory import get_resilient_routing_provider
from app.integrations.maps.interface import RoutingProviderInterface
from app.schemas.location import RouteResult, TravelMode

logger = logging.getLogger("ada.services.routing")


class RoutingService:
    """
    Routing Service coordinating transit and driving directions across
    Google Maps and Mapbox provider adapters.
    Maintains 5-minute TTL caching in Redis for traffic responsiveness,
    enforces privacy-by-design coordinate fuzzing, and strictly isolates
    provider logic from domain workflows.
    """

    def __init__(self, provider: Optional[RoutingProviderInterface] = None):
        self.provider = provider or get_resilient_routing_provider()

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TravelMode = TravelMode.DRIVING,
        departure_time: Optional[int] = None,
    ) -> RouteResult:
        # Validate coordinate boundaries
        for lat, name in [(origin_lat, "Origin latitude"), (dest_lat, "Destination latitude")]:
            if not (-90.0 <= lat <= 90.0):
                raise ValidationException(f"{name} must be between -90.0 and 90.0 degrees.")

        for lng, name in [(origin_lng, "Origin longitude"), (dest_lng, "Destination longitude")]:
            if not (-180.0 <= lng <= 180.0):
                raise ValidationException(f"{name} must be between -180.0 and 180.0 degrees.")

        mode_str = mode.value if hasattr(mode, "value") else str(mode)
        # Cache key rounded to ~11 meters for privacy and cache hits
        cache_key = (
            f"cache:route:{round(origin_lat, 4)}:{round(origin_lng, 4)}:"
            f"{round(dest_lat, 4)}:{round(dest_lng, 4)}:{mode_str}"
        )

        # 1. Attempt Redis Read (only if near-current departure)
        if departure_time is None:
            try:
                redis_client = get_redis_client()
                cached = redis_client.get(cache_key)
                if cached:
                    logger.debug(f"Redis cache hit for route ({mode_str})")
                    return RouteResult.model_validate(json.loads(cached))
            except Exception as e:
                logger.debug(f"Redis read skipped for route cache: {e}")

        # 2. Query Resilient Routing Network
        route = await self.provider.calculate_route(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            mode=mode,
            departure_time=departure_time,
        )

        # 3. Write Back to Cache with 5-minute TTL
        if departure_time is None:
            try:
                redis_client = get_redis_client()
                redis_client.set(
                    cache_key,
                    json.dumps(route.model_dump()),
                    ex=settings.ROUTE_CACHE_TTL_SECONDS,
                )
            except Exception as e:
                logger.debug(f"Redis write skipped for route cache: {e}")

        return route

