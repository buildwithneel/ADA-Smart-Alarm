from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, status

from app.api.deps import get_geocoding_service, get_routing_service
from app.core.errors import NotFoundException
from app.core.rate_limit import rate_limit_dependency
from app.integrations.maps.factory import check_all_providers_health
from app.schemas.location import (
    GeocodeSearchRequest,
    GeocodingResult,
    ProviderHealthResponse,
    ReverseGeocodeRequest,
    RouteRequest,
    RouteResult,
)
from app.services.geocoding_service import GeocodingService
from app.services.routing_service import RoutingService

router = APIRouter()


@router.get(
    "/location/health",
    response_model=ProviderHealthResponse,
    summary="Provider Infrastructure Health Check",
    tags=["Location & Maps"],
)
async def get_location_provider_health() -> ProviderHealthResponse:
    """
    Evaluates availability and readiness of external maps, routing,
    and geocoding providers without exposing internal credentials.
    """
    return await check_all_providers_health()


@router.post(
    "/geocoding/search",
    response_model=List[GeocodingResult],
    summary="Forward Geocode Destination Search",
    tags=["Location & Maps"],
    dependencies=[Depends(rate_limit_dependency(prefix="geocode_search"))],
)
async def search_geocoding(
    payload: GeocodeSearchRequest,
    geocoding_service: GeocodingService = Depends(get_geocoding_service),
) -> List[GeocodingResult]:
    """
    Resolves an address, landmark, or query string into candidate coordinates.
    Protected by Redis sliding-window rate limiting and 24-hour result caching.
    """
    return await geocoding_service.search(query=payload.query, limit=payload.limit)


@router.post(
    "/geocoding/reverse",
    response_model=GeocodingResult,
    summary="Reverse Geocode GPS Coordinates",
    tags=["Location & Maps"],
    dependencies=[Depends(rate_limit_dependency(prefix="geocode_rev"))],
)
async def reverse_geocode(
    payload: ReverseGeocodeRequest,
    geocoding_service: GeocodingService = Depends(get_geocoding_service),
) -> GeocodingResult:
    """
    Converts GPS latitude and longitude into a readable normalized address line.
    Fuzzes coordinate resolution to ~11m to preserve location privacy.
    """
    result = await geocoding_service.reverse_geocode(
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    if not result:
        raise NotFoundException("Address", f"{payload.latitude}, {payload.longitude}")
    return result


@router.post(
    "/routes",
    response_model=RouteResult,
    summary="Calculate Route and Traffic Travel Duration",
    tags=["Location & Maps"],
    dependencies=[Depends(rate_limit_dependency(prefix="routes"))],
)
async def calculate_route(
    payload: RouteRequest,
    routing_service: RoutingService = Depends(get_routing_service),
) -> RouteResult:
    """
    Computes distance, baseline duration, and traffic-aware travel duration
    across configured Google Maps or Mapbox providers with resilient failover.
    Cached for 5 minutes in Redis for live traffic responsiveness.
    """
    return await routing_service.calculate_route(
        origin_lat=payload.origin.latitude,
        origin_lng=payload.origin.longitude,
        dest_lat=payload.destination.latitude,
        dest_lng=payload.destination.longitude,
        mode=payload.travel_mode,
        departure_time=payload.departure_time,
    )
