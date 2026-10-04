from __future__ import annotations

import hashlib
import json
import logging
from typing import List, Optional

from app.core.config import settings
from app.core.errors import ValidationException
from app.core.redis import get_redis_client
from app.integrations.maps.factory import get_resilient_geocoding_provider
from app.integrations.maps.interface import GeocodingProviderInterface
from app.schemas.location import GeocodingResult

logger = logging.getLogger("ada.services.geocoding")


class GeocodingService:
    """
    Geocoding Service managing forward and reverse address resolution.
    Applies privacy-by-design coordinate fuzzing for caching,
    Redis caching with 24-hour TTL, and resilient multi-provider failover.
    """

    def __init__(self, provider: Optional[GeocodingProviderInterface] = None):
        self.provider = provider or get_resilient_geocoding_provider()

    async def search(self, query: str, limit: int = 5) -> List[GeocodingResult]:
        cleaned = " ".join(query.strip().split())
        if len(cleaned) < 2:
            raise ValidationException("Search query must be at least 2 characters.")

        limit = max(1, min(limit, 20))
        cache_key = f"cache:geocode:search:{hashlib.sha256(cleaned.lower().encode()).hexdigest()}:{limit}"

        # 1. Attempt Redis Cache Hit
        try:
            redis_client = get_redis_client()
            cached = redis_client.get(cache_key)
            if cached:
                raw_items = json.loads(cached)
                logger.debug(f"Redis cache hit for query: '{cleaned}'")
                return [GeocodingResult.model_validate(item) for item in raw_items]
        except Exception as e:
            logger.debug(f"Redis read skipped for geocode cache: {e}")

        # 2. Query Resilient Provider Network
        results = await self.provider.geocode(cleaned, limit)

        # 3. Write Back to Cache
        try:
            redis_client = get_redis_client()
            serialized = json.dumps([r.model_dump() for r in results])
            redis_client.set(cache_key, serialized, ex=settings.GEOCODING_CACHE_TTL_SECONDS)
        except Exception as e:
            logger.debug(f"Redis write skipped for geocode cache: {e}")

        return results

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[GeocodingResult]:
        if not (-90.0 <= latitude <= 90.0):
            raise ValidationException("Latitude must be between -90.0 and 90.0 degrees.")
        if not (-180.0 <= longitude <= 180.0):
            raise ValidationException("Longitude must be between -180.0 and 180.0 degrees.")

        # Privacy & Cache Fuzzing: 4 decimal places gives ~11m precision
        round_lat = round(latitude, 4)
        round_lng = round(longitude, 4)
        cache_key = f"cache:geocode:rev:{round_lat}:{round_lng}"

        # 1. Attempt Redis Cache Hit
        try:
            redis_client = get_redis_client()
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"Redis cache hit for reverse geocode: {round_lat}, {round_lng}")
                return GeocodingResult.model_validate(json.loads(cached))
        except Exception as e:
            logger.debug(f"Redis read skipped for reverse geocode cache: {e}")

        # 2. Query Resilient Provider Network
        result = await self.provider.reverse_geocode(latitude, longitude)

        # 3. Write Back to Cache
        if result:
            try:
                redis_client = get_redis_client()
                redis_client.set(
                    cache_key,
                    json.dumps(result.model_dump()),
                    ex=settings.GEOCODING_CACHE_TTL_SECONDS,
                )
            except Exception as e:
                logger.debug(f"Redis write skipped for reverse geocode cache: {e}")

        return result

