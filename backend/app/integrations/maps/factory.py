from __future__ import annotations

from typing import Dict, Tuple

from app.core.config import settings
from app.integrations.maps.google_maps import GoogleMapsProvider
from app.integrations.maps.interface import (
    GeocodingProviderInterface,
    RoutingProviderInterface,
)
from app.integrations.maps.mapbox import MapboxProvider
from app.integrations.maps.resilient import (
    ResilientGeocodingProvider,
    ResilientRoutingProvider,
)
from app.schemas.location import ProviderHealthResponse, ProviderStatus


def get_map_providers() -> Tuple[GoogleMapsProvider, MapboxProvider]:
    """Instantiates concrete Google and Mapbox provider instances."""
    google = GoogleMapsProvider(api_key=settings.GOOGLE_MAPS_API_KEY)
    mapbox = MapboxProvider(access_token=settings.MAPBOX_ACCESS_TOKEN)
    return google, mapbox


def get_resilient_routing_provider() -> RoutingProviderInterface:
    """
    Constructs the active resilient routing provider based on settings.
    Default: Google primary, Mapbox fallback.
    """
    google, mapbox = get_map_providers()

    if settings.ROUTING_PROVIDER.lower() == "mapbox":
        primary, fallback = mapbox, google
    else:
        primary, fallback = google, mapbox

    return ResilientRoutingProvider(
        primary=primary,
        fallback=fallback,
        enable_fallback=settings.ENABLE_PROVIDER_FALLBACK,
    )


def get_resilient_geocoding_provider() -> GeocodingProviderInterface:
    """
    Constructs the active resilient geocoding provider based on settings.
    Default: Google primary, Mapbox fallback.
    """
    google, mapbox = get_map_providers()

    if settings.GEOCODING_PROVIDER.lower() == "mapbox":
        primary, fallback = mapbox, google
    else:
        primary, fallback = google, mapbox

    return ResilientGeocodingProvider(
        primary=primary,
        fallback=fallback,
        enable_fallback=settings.ENABLE_PROVIDER_FALLBACK,
    )


async def check_all_providers_health() -> ProviderHealthResponse:
    """
    Evaluates health of both Google and Mapbox providers without exposing
    secrets or tokens.
    """
    google, mapbox = get_map_providers()

    g_health = await google.check_health()
    m_health = await mapbox.check_health()

    providers: Dict[str, ProviderStatus] = {
        "google": g_health,
        "mapbox": m_health,
    }

    # Determine overall status
    primary_name = settings.ROUTING_PROVIDER.lower()
    primary_status = providers.get(primary_name, g_health).status

    fallback_name = settings.ROUTING_FALLBACK_PROVIDER.lower()
    fallback_status = providers.get(fallback_name, m_health).status

    if primary_status == "available":
        overall = "healthy"
    elif fallback_status == "available" and settings.ENABLE_PROVIDER_FALLBACK:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return ProviderHealthResponse(
        status=overall,
        primary_routing_provider=settings.ROUTING_PROVIDER,
        fallback_routing_provider=settings.ROUTING_FALLBACK_PROVIDER,
        primary_geocoding_provider=settings.GEOCODING_PROVIDER,
        fallback_geocoding_provider=settings.GEOCODING_FALLBACK_PROVIDER,
        fallback_enabled=settings.ENABLE_PROVIDER_FALLBACK,
        providers=providers,
    )
