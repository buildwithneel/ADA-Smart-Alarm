from __future__ import annotations

import logging
from typing import List, Optional

from app.core.errors import (
    AppException,
    NoRouteFoundException,
    ProviderException,
    UnsupportedTravelModeException,
)
from app.integrations.maps.interface import (
    GeocodingProviderInterface,
    RoutingProviderInterface,
)
from app.schemas.location import (
    GeocodingResult,
    ProviderStatus,
    RouteResult,
    TravelMode,
)

logger = logging.getLogger("ada.maps.resilient")


class ResilientRoutingProvider(RoutingProviderInterface):
    """
    Resilient Routing Provider implementing automatic failover.
    Executes primary routing provider; if it encounters outage, timeout,
    rate limiting, or an unsupported travel mode, seamlessly falls back
    to secondary provider while tagging the resulting provider identity.
    """

    def __init__(
        self,
        primary: RoutingProviderInterface,
        fallback: Optional[RoutingProviderInterface] = None,
        enable_fallback: bool = True,
    ):
        self.primary = primary
        self.fallback = fallback
        self.enable_fallback = enable_fallback

    @property
    def name(self) -> str:
        return f"{self.primary.name}_resilient"

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TravelMode = TravelMode.DRIVING,
        departure_time: Optional[int] = None,
    ) -> RouteResult:
        try:
            return await self.primary.calculate_route(
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                dest_lat=dest_lat,
                dest_lng=dest_lng,
                mode=mode,
                departure_time=departure_time,
            )
        except (ProviderException, UnsupportedTravelModeException, Exception) as primary_err:
            if not self.enable_fallback or not self.fallback:
                logger.error(
                    f"Routing provider '{self.primary.name}' failed and no fallback available: {primary_err}"
                )
                raise

            # If it was an explicit NoRouteFoundException, don't fallback unless unsupported mode
            if isinstance(primary_err, NoRouteFoundException):
                raise

            logger.warning(
                f"Primary routing provider '{self.primary.name}' failed ({type(primary_err).__name__}: {primary_err}). "
                f"Attempting fallback to '{self.fallback.name}'..."
            )

            try:
                fallback_res = await self.fallback.calculate_route(
                    origin_lat=origin_lat,
                    origin_lng=origin_lng,
                    dest_lat=dest_lat,
                    dest_lng=dest_lng,
                    mode=mode,
                    departure_time=departure_time,
                )
                logger.info(
                    f"Fallback routing succeeded via provider '{self.fallback.name}'."
                )
                return fallback_res
            except Exception as fallback_err:
                logger.error(
                    f"Both primary ('{self.primary.name}') and fallback ('{self.fallback.name}') routing failed. "
                    f"Primary: {primary_err} | Fallback: {fallback_err}"
                )
                raise ProviderException(
                    message=f"Routing unavailable across providers: {str(fallback_err)}",
                    provider="all",
                )

    async def check_health(self) -> ProviderStatus:
        return await self.primary.check_health()


class ResilientGeocodingProvider(GeocodingProviderInterface):
    """
    Resilient Geocoding Provider implementing automatic failover for forward
    and reverse address lookups.
    """

    def __init__(
        self,
        primary: GeocodingProviderInterface,
        fallback: Optional[GeocodingProviderInterface] = None,
        enable_fallback: bool = True,
    ):
        self.primary = primary
        self.fallback = fallback
        self.enable_fallback = enable_fallback

    @property
    def name(self) -> str:
        return f"{self.primary.name}_resilient"

    async def geocode(self, query: str, limit: int = 5) -> List[GeocodingResult]:
        try:
            results = await self.primary.geocode(query, limit)
            if results or not self.enable_fallback or not self.fallback:
                return results
            logger.info(
                f"Primary geocoder '{self.primary.name}' returned 0 results. Checking fallback '{self.fallback.name}'..."
            )
            return await self.fallback.geocode(query, limit)
        except Exception as primary_err:
            if not self.enable_fallback or not self.fallback:
                logger.error(f"Geocoding provider '{self.primary.name}' failed: {primary_err}")
                raise

            logger.warning(
                f"Primary geocoder '{self.primary.name}' failed ({primary_err}). "
                f"Falling back to '{self.fallback.name}'..."
            )
            try:
                return await self.fallback.geocode(query, limit)
            except Exception as fallback_err:
                logger.error(f"Both geocoding providers failed: {fallback_err}")
                raise ProviderException(
                    message="Geocoding service unavailable across all providers",
                    provider="all",
                )

    async def reverse_geocode(self, lat: float, lng: float) -> Optional[GeocodingResult]:
        try:
            res = await self.primary.reverse_geocode(lat, lng)
            if res is not None or not self.enable_fallback or not self.fallback:
                return res
            logger.info(
                f"Primary reverse geocoder '{self.primary.name}' returned None. Checking fallback..."
            )
            return await self.fallback.reverse_geocode(lat, lng)
        except Exception as primary_err:
            if not self.enable_fallback or not self.fallback:
                logger.error(f"Reverse geocoding provider '{self.primary.name}' failed: {primary_err}")
                raise

            logger.warning(
                f"Primary reverse geocoder '{self.primary.name}' failed ({primary_err}). "
                f"Falling back to '{self.fallback.name}'..."
            )
            try:
                return await self.fallback.reverse_geocode(lat, lng)
            except Exception as fallback_err:
                logger.error(f"Both reverse geocoding providers failed: {fallback_err}")
                raise ProviderException(
                    message="Reverse geocoding service unavailable",
                    provider="all",
                )

    async def check_health(self) -> ProviderStatus:
        return await self.primary.check_health()
