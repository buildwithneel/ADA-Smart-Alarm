from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.schemas.location import (
    GeocodingResult,
    ProviderStatus,
    RouteResult,
    TravelMode,
)


class GeocodingProviderInterface(ABC):
    """
    Abstract interface for external forward and reverse geocoding providers.
    Ensures decoupled provider implementations (Google Geocoding, Mapbox Places).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier ('google', 'mapbox')."""
        pass

    @abstractmethod
    async def geocode(self, query: str, limit: int = 5) -> List[GeocodingResult]:
        """Forward geocodes an address or query to normalized coordinate results."""
        pass

    @abstractmethod
    async def reverse_geocode(self, lat: float, lng: float) -> Optional[GeocodingResult]:
        """Reverse geocodes coordinate pair into normalized human-readable address."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderStatus:
        """Verifies provider credentials and connectivity health."""
        pass


class RoutingProviderInterface(ABC):
    """
    Abstract interface for external directions and traffic-aware routing providers.
    Separates base travel duration from real-time traffic delay.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier ('google', 'mapbox')."""
        pass

    @abstractmethod
    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TravelMode = TravelMode.DRIVING,
        departure_time: Optional[int] = None,
    ) -> RouteResult:
        """Calculates normalized route polyline, distance, and duration."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderStatus:
        """Verifies provider credentials and routing connectivity."""
        pass


class MapProviderInterface(GeocodingProviderInterface, RoutingProviderInterface, ABC):
    """Combined map services interface."""
    pass
