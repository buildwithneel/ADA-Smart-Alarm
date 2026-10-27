from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from app.schemas.base import BaseSchema


class Location(BaseSchema):
    """
    Normalized Geographical Location coordinates and optional telemetry.
    Strictly bounds latitude [-90, 90] and longitude [-180, 180].
    Optional telemetry (altitude, heading, speed) is explicitly nullable
    as mobile browsers and desktop clients may omit them.
    """
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in degrees (-180 to 180)")
    accuracy_meters: Optional[float] = Field(None, ge=0.0, description="GPS horizontal accuracy in meters")
    altitude: Optional[float] = Field(None, description="Altitude above sea level in meters")
    heading: Optional[float] = Field(None, ge=0.0, le=360.0, description="Direction of travel in degrees")
    speed: Optional[float] = Field(None, ge=0.0, description="Instantaneous velocity in meters per second")
    timestamp: Optional[int] = Field(None, description="Unix millisecond timestamp when position was recorded")


class TravelMode(str, enum.Enum):
    """
    Normalized travel modalities supported across provider network.
    """
    DRIVING = "driving"
    WALKING = "walking"
    CYCLING = "cycling"
    TRANSIT = "transit"


class GeocodeSearchRequest(BaseSchema):
    query: str = Field(..., min_length=2, max_length=300, description="Address or landmark query string")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of candidate suggestions")


class ReverseGeocodeRequest(BaseSchema):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate")


class GeocodingResult(BaseSchema):
    """
    Normalized Geocoding entity produced by Google Places / Geocoding or Mapbox Geocoding.
    """
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    formatted_address: str = Field(..., description="Full human-readable address line")
    place_id: Optional[str] = Field(None, description="Vendor or platform specific place ID")
    provider: str = Field(..., description="Provider name: 'google' or 'mapbox'")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Match confidence score [0.0 - 1.0]")


class RouteRequest(BaseSchema):
    origin: Location
    destination: Location
    travel_mode: TravelMode = Field(default=TravelMode.DRIVING, description="Mode of transport")
    departure_time: Optional[int] = Field(None, description="Optional unix timestamp seconds for departure")


class RouteStep(BaseSchema):
    instruction: str
    distance_meters: int
    duration_seconds: int


class RouteSummary(BaseSchema):
    formatted_distance: str
    formatted_duration: str
    formatted_traffic_delay: str
    congestion_level: str = Field(..., description="low, moderate, heavy, or severe")


class RouteResult(BaseSchema):
    """
    Normalized Route Result decoupling Google Routes and Mapbox Directions.
    Separates base duration from traffic-aware duration for the future ETA Engine.
    """
    origin: Dict[str, float]
    destination: Dict[str, float]
    distance_meters: int
    duration_seconds: int  # Base travel duration without congestion
    traffic_duration_seconds: int  # Traffic-aware duration with current road conditions
    route_geometry: str  # Encoded polyline or coordinate string
    provider: str  # Which provider successfully resolved this ("google" | "mapbox")
    is_traffic_aware: bool = Field(default=False, description="Whether live traffic conditions were factored in")
    timestamp: str  # ISO-8601 calculation timestamp
    travel_mode: str
    summary: RouteSummary
    steps: Optional[List[RouteStep]] = None
    alternative_routes: Optional[List[Dict[str, Any]]] = None


class ProviderStatus(BaseSchema):
    name: str
    status: str  # available, unavailable, rate_limited, auth_failed, timeout
    configured: bool
    message: Optional[str] = None


class ProviderHealthResponse(BaseSchema):
    status: str  # healthy, degraded, unhealthy
    primary_routing_provider: str
    fallback_routing_provider: str
    primary_geocoding_provider: str
    fallback_geocoding_provider: str
    fallback_enabled: bool
    providers: Dict[str, ProviderStatus]
