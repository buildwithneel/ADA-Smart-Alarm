from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.core.errors import (
    NoRouteFoundException,
    ProviderException,
    RateLimitExceededException,
    UnsupportedTravelModeException,
)
from app.integrations.maps.google_maps import GoogleMapsProvider
from app.integrations.maps.mapbox import MapboxProvider
from app.integrations.maps.resilient import (
    ResilientGeocodingProvider,
    ResilientRoutingProvider,
)
from app.schemas.location import (
    GeocodingResult,
    Location,
    RouteResult,
    TravelMode,
)
from app.services.geocoding_service import GeocodingService
from app.services.routing_service import RoutingService


# =========================================================================
# 1. Location Normalization & Validation Tests
# =========================================================================
def test_location_model_validation_valid():
    loc = Location(
        latitude=22.5996,
        longitude=72.8205,
        accuracy_meters=15.2,
        altitude=45.0,
        heading=180.0,
        speed=12.5,
        timestamp=1690000000000,
    )
    assert loc.latitude == 22.5996
    assert loc.longitude == 72.8205
    assert loc.accuracy_meters == 15.2
    assert loc.speed == 12.5


def test_location_model_null_telemetry():
    """Optional telemetry fields must be nullable for privacy and device variance."""
    loc = Location(latitude=23.0, longitude=72.0)
    assert loc.accuracy_meters is None
    assert loc.altitude is None
    assert loc.heading is None
    assert loc.speed is None
    assert loc.timestamp is None


def test_location_invalid_latitude():
    with pytest.raises(Exception):
        Location(latitude=95.0, longitude=72.0)

    with pytest.raises(Exception):
        Location(latitude=-91.0, longitude=72.0)


def test_location_invalid_longitude():
    with pytest.raises(Exception):
        Location(latitude=22.0, longitude=185.0)

    with pytest.raises(Exception):
        Location(latitude=22.0, longitude=-181.0)


# =========================================================================
# 2. Provider Normalization Tests (Google & Mapbox)
# =========================================================================
@pytest.mark.asyncio
async def test_google_maps_provider_geocode_simulation():
    provider = GoogleMapsProvider()
    results = await provider.geocode("CHARUSAT University")
    assert len(results) > 0
    first = results[0]
    assert isinstance(first, GeocodingResult)
    assert first.provider == "google"
    assert "CHARUSAT" in first.formatted_address
    assert pytest.approx(first.latitude, 0.01) == 22.5996
    assert pytest.approx(first.longitude, 0.01) == 72.8205


@pytest.mark.asyncio
async def test_google_maps_provider_reverse_geocode_simulation():
    provider = GoogleMapsProvider()
    result = await provider.reverse_geocode(22.5996, 72.8205)
    assert result is not None
    assert result.provider == "google"
    assert "CHARUSAT" in result.formatted_address


@pytest.mark.asyncio
async def test_google_maps_provider_route_simulation():
    provider = GoogleMapsProvider()
    res = await provider.calculate_route(
        origin_lat=23.2156,
        origin_lng=72.6369,
        dest_lat=22.5996,
        dest_lng=72.8205,
        mode=TravelMode.DRIVING,
    )
    assert isinstance(res, RouteResult)
    assert res.provider == "google"
    assert res.distance_meters > 50000  # Gandhinagar to Changa > 50km
    assert res.duration_seconds > 0
    assert res.traffic_duration_seconds >= res.duration_seconds
    assert res.route_geometry != ""
    assert res.summary.formatted_duration is not None


@pytest.mark.asyncio
async def test_mapbox_provider_geocode_simulation():
    provider = MapboxProvider()
    results = await provider.geocode("Changa")
    assert len(results) > 0
    first = results[0]
    assert first.provider == "mapbox"
    assert pytest.approx(first.latitude, 0.05) == 22.60


@pytest.mark.asyncio
async def test_mapbox_provider_route_simulation():
    provider = MapboxProvider()
    res = await provider.calculate_route(
        origin_lat=23.2156,
        origin_lng=72.6369,
        dest_lat=22.5996,
        dest_lng=72.8205,
        mode=TravelMode.DRIVING,
    )
    assert isinstance(res, RouteResult)
    assert res.provider == "mapbox"
    assert res.traffic_duration_seconds >= res.duration_seconds


@pytest.mark.asyncio
async def test_mapbox_rejects_unsupported_transit_mode():
    """Mapbox Directions does not support public transit; must raise UnsupportedTravelModeException."""
    provider = MapboxProvider()
    with pytest.raises(UnsupportedTravelModeException) as exc_info:
        await provider.calculate_route(
            origin_lat=23.2156,
            origin_lng=72.6369,
            dest_lat=22.5996,
            dest_lng=72.8205,
            mode=TravelMode.TRANSIT,
        )
    assert exc_info.value.details["mode"] == "transit"
    assert exc_info.value.details["provider"] == "mapbox"


# =========================================================================
# 3. Provider Failover / Resilient Fallback Tests
# =========================================================================
@pytest.mark.asyncio
async def test_resilient_routing_fallback_on_primary_outage():
    mock_primary = MagicMock()
    mock_primary.name = "failing_primary"
    mock_primary.calculate_route = AsyncMock(
        side_effect=ProviderException("Upstream 503 Outage", provider="failing_primary")
    )

    mock_fallback = MagicMock()
    mock_fallback.name = "healthy_fallback"
    expected_route = RouteResult(
        origin={"latitude": 23.0, "longitude": 72.0},
        destination={"latitude": 22.6, "longitude": 72.8},
        distance_meters=55000,
        duration_seconds=3600,
        traffic_duration_seconds=4200,
        route_geometry="polyline_geometry_mock",
        provider="healthy_fallback",
        timestamp="2026-09-30T12:00:00Z",
        travel_mode="driving",
        summary={
            "formatted_distance": "55 km",
            "formatted_duration": "70 min",
            "formatted_traffic_delay": "+10 min",
            "congestion_level": "moderate",
        },
    )
    mock_fallback.calculate_route = AsyncMock(return_value=expected_route)

    resilient = ResilientRoutingProvider(primary=mock_primary, fallback=mock_fallback, enable_fallback=True)

    result = await resilient.calculate_route(
        origin_lat=23.0,
        origin_lng=72.0,
        dest_lat=22.6,
        dest_lng=72.8,
        mode=TravelMode.DRIVING,
    )

    assert result.provider == "healthy_fallback"
    assert result.traffic_duration_seconds == 4200
    mock_primary.calculate_route.assert_called_once()
    mock_fallback.calculate_route.assert_called_once()


@pytest.mark.asyncio
async def test_resilient_routing_fallback_on_unsupported_mode():
    """If primary (e.g. Mapbox) rejects transit, fallback (e.g. Google) fulfills it."""
    mapbox = MapboxProvider()
    google = GoogleMapsProvider()

    resilient = ResilientRoutingProvider(primary=mapbox, fallback=google, enable_fallback=True)

    res = await resilient.calculate_route(
        origin_lat=23.2156,
        origin_lng=72.6369,
        dest_lat=22.5996,
        dest_lng=72.8205,
        mode=TravelMode.TRANSIT,
    )
    assert res.provider == "google"
    assert res.travel_mode == "transit"


@pytest.mark.asyncio
async def test_resilient_geocoding_fallback():
    mock_primary = MagicMock()
    mock_primary.name = "failing_geocoder"
    mock_primary.geocode = AsyncMock(side_effect=ProviderException("Timeout", provider="failing_geocoder"))

    mock_fallback = MagicMock()
    mock_fallback.name = "fallback_geocoder"
    mock_fallback.geocode = AsyncMock(
        return_value=[
            GeocodingResult(
                latitude=22.5996,
                longitude=72.8205,
                formatted_address="CHARUSAT Campus",
                place_id="fb_123",
                provider="fallback_geocoder",
                confidence=0.99,
            )
        ]
    )

    resilient = ResilientGeocodingProvider(primary=mock_primary, fallback=mock_fallback, enable_fallback=True)
    res = await resilient.geocode("CHARUSAT")
    assert len(res) == 1
    assert res[0].provider == "fallback_geocoder"


# =========================================================================
# 4. Service Layer & Caching Tests
# =========================================================================
@pytest.mark.asyncio
async def test_routing_service_separation_of_base_and_traffic_duration():
    service = RoutingService()
    res = await service.calculate_route(
        origin_lat=23.2156,
        origin_lng=72.6369,
        dest_lat=22.5996,
        dest_lng=72.8205,
        mode=TravelMode.DRIVING,
    )
    # Base duration and traffic duration must be separated for ETA Engine
    assert res.duration_seconds > 0
    assert res.traffic_duration_seconds > 0
    assert res.traffic_duration_seconds >= res.duration_seconds


@pytest.mark.asyncio
async def test_geocoding_service_rejects_empty_query():
    service = GeocodingService()
    with pytest.raises(Exception):
        await service.search(" ")


# =========================================================================
# 5. FastAPI Endpoints Integration Tests
# =========================================================================
def test_location_health_endpoint(client: TestClient):
    response = client.get("/api/v1/location/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "google" in data["providers"]
    assert "mapbox" in data["providers"]


def test_geocoding_search_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/geocoding/search",
        json={"query": "CHARUSAT", "limit": 3},
    )
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) > 0
    assert "latitude" in results[0]
    assert "longitude" in results[0]
    assert "formatted_address" in results[0]
    assert results[0]["provider"] in ["google", "mapbox"]


def test_geocoding_reverse_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/geocoding/reverse",
        json={"latitude": 22.5996, "longitude": 72.8205},
    )
    assert response.status_code == 200
    data = response.json()
    assert "formatted_address" in data
    assert data["latitude"] == 22.5996
    assert data["longitude"] == 72.8205


def test_routes_calculation_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/routes",
        json={
            "origin": {"latitude": 23.2156, "longitude": 72.6369},
            "destination": {"latitude": 22.5996, "longitude": 72.8205},
            "travel_mode": "driving",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "distance_meters" in data
    assert "duration_seconds" in data
    assert "traffic_duration_seconds" in data
    assert data["traffic_duration_seconds"] >= data["duration_seconds"]
    assert "route_geometry" in data
    assert data["provider"] in ["google", "mapbox"]


def test_routes_calculation_transit_fallback_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/routes",
        json={
            "origin": {"latitude": 23.2156, "longitude": 72.6369},
            "destination": {"latitude": 22.5996, "longitude": 72.8205},
            "travel_mode": "transit",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["travel_mode"] == "transit"
    assert data["provider"] == "google"  # Google supports transit
