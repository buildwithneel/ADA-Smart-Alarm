from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.errors import (
    NoRouteFoundException,
    ProviderException,
    UnsupportedTravelModeException,
)
from app.integrations.maps.interface import MapProviderInterface
from app.integrations.maps.utils import (
    calculate_congestion_level,
    create_simple_encoded_polyline,
    estimate_speed_meters_per_sec,
    format_distance_meters,
    format_duration_seconds,
    haversine_distance_meters,
)
from app.schemas.location import (
    GeocodingResult,
    ProviderStatus,
    RouteResult,
    RouteStep,
    RouteSummary,
    TravelMode,
)

logger = logging.getLogger("ada.maps.mapbox")


class MapboxProvider(MapProviderInterface):
    """
    Mapbox Platform implementation:
    - Geocoding API v5 (Forward & Reverse)
    - Directions API v5 (mapbox/driving-traffic, mapbox/walking, mapbox/cycling)
    - Rejects unsupported travel modes (e.g. transit) adhering to domain rules
    - Offline fallback simulation when access token is unconfigured
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or settings.MAPBOX_ACCESS_TOKEN
        self.timeout = settings.PROVIDER_TIMEOUT_SECONDS

    @property
    def name(self) -> str:
        return "mapbox"

    async def geocode(self, query: str, limit: int = 5) -> List[GeocodingResult]:
        if not self.access_token:
            return self._simulate_geocode(query, limit)

        encoded_query = httpx.URL(f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json").path
        url = f"https://api.mapbox.com{encoded_query}"
        params = {"access_token": self.access_token, "limit": limit}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 401 or resp.status_code == 403:
                    raise ProviderException("Mapbox access token invalid or unauthorized", provider=self.name)
                elif resp.status_code == 429:
                    raise ProviderException("Mapbox rate limit exceeded", provider=self.name)
                elif resp.status_code != 200:
                    raise ProviderException(f"Mapbox Geocoding HTTP {resp.status_code}", provider=self.name)
                data = resp.json()

            features = data.get("features", [])
            results: List[GeocodingResult] = []
            for feat in features[:limit]:
                center = feat.get("center", [0, 0])
                results.append(
                    GeocodingResult(
                        latitude=center[1],
                        longitude=center[0],
                        formatted_address=feat.get("place_name", query),
                        place_id=feat.get("id"),
                        provider=self.name,
                        confidence=feat.get("relevance", 0.9),
                    )
                )
            return results

        except httpx.TimeoutException:
            raise ProviderException("Mapbox Geocoding timeout", provider=self.name)
        except httpx.RequestError as e:
            raise ProviderException(f"Mapbox Geocoding network error: {str(e)}", provider=self.name)

    async def reverse_geocode(self, lat: float, lng: float) -> Optional[GeocodingResult]:
        if not self.access_token:
            return self._simulate_reverse_geocode(lat, lng)

        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
        params = {"access_token": self.access_token, "limit": 1}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    raise ProviderException(f"Mapbox Reverse Geocoding HTTP {resp.status_code}", provider=self.name)
                data = resp.json()

            features = data.get("features", [])
            if not features:
                return None

            feat = features[0]
            center = feat.get("center", [lng, lat])
            return GeocodingResult(
                latitude=center[1],
                longitude=center[0],
                formatted_address=feat.get("place_name", f"{lat:.4f}, {lng:.4f}"),
                place_id=feat.get("id"),
                provider=self.name,
                confidence=feat.get("relevance", 1.0),
            )
        except httpx.TimeoutException:
            raise ProviderException("Mapbox Reverse Geocoding timeout", provider=self.name)
        except httpx.RequestError as e:
            raise ProviderException(f"Mapbox Reverse Geocoding network error: {str(e)}", provider=self.name)

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: Any = TravelMode.DRIVING,
        departure_time: Optional[int] = None,
    ) -> RouteResult:
        mode_val = mode.value if hasattr(mode, "value") else str(mode)
        # Mapbox standard directions do not support public transport
        if mode_val == "transit":
            raise UnsupportedTravelModeException(mode="transit", provider=self.name)

        if not self.access_token:
            return self._simulate_route(origin_lat, origin_lng, dest_lat, dest_lng, mode_val)

        profile_map = {
            "driving": "mapbox/driving-traffic",
            "walking": "mapbox/walking",
            "cycling": "mapbox/cycling",
        }
        profile = profile_map.get(mode_val, "mapbox/driving-traffic")

        url = f"https://api.mapbox.com/directions/v5/{profile}/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"

        params = {
            "access_token": self.access_token,
            "overview": "full",
            "steps": "true",
            "geometries": "polyline",
            "annotations": "duration",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    raise ProviderException("Mapbox rate limit exceeded", provider=self.name)
                elif resp.status_code != 200:
                    raise ProviderException(f"Mapbox Directions HTTP {resp.status_code}", provider=self.name)
                data = resp.json()

            code = data.get("code")
            if code == "NoRoute":
                raise NoRouteFoundException()
            elif code != "Ok":
                raise ProviderException(f"Mapbox error: {code}", provider=self.name)

            routes = data.get("routes", [])
            if not routes:
                raise NoRouteFoundException()

            route = routes[0]
            dist_meters = int(round(route.get("distance", 0)))
            # duration incorporates traffic when using driving-traffic profile
            traffic_sec = int(round(route.get("duration", 0)))
            # duration_typical or fallback to 80% of traffic
            duration_sec = int(round(route.get("duration_typical", traffic_sec * 0.85 if mode == TravelMode.DRIVING else traffic_sec)))
            traffic_delay = max(0, traffic_sec - duration_sec)
            congestion = calculate_congestion_level(traffic_delay)

            steps: List[RouteStep] = []
            for leg in route.get("legs", []):
                for s in leg.get("steps", []):
                    maneuver = s.get("maneuver", {}).get("instruction", "Proceed along route")
                    steps.append(
                        RouteStep(
                            instruction=maneuver,
                            distance_meters=int(round(s.get("distance", 0))),
                            duration_seconds=int(round(s.get("duration", 0))),
                        )
                    )

            return RouteResult(
                origin={"latitude": origin_lat, "longitude": origin_lng},
                destination={"latitude": dest_lat, "longitude": dest_lng},
                distance_meters=dist_meters,
                duration_seconds=duration_sec,
                traffic_duration_seconds=traffic_sec,
                route_geometry=route.get("geometry", ""),
                provider=self.name,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                travel_mode=mode.value,
                summary=RouteSummary(
                    formatted_distance=format_distance_meters(dist_meters),
                    formatted_duration=format_duration_seconds(traffic_sec),
                    formatted_traffic_delay=f"+{int(round(traffic_delay / 60))} min" if traffic_delay > 60 else "No delay",
                    congestion_level=congestion,
                ),
                steps=steps,
            )

        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise ProviderException(f"Mapbox Directions network error: {str(e)}", provider=self.name)

    async def check_health(self) -> ProviderStatus:
        if not self.access_token:
            return ProviderStatus(
                name=self.name,
                status="available",
                configured=False,
                message="Mapbox running in offline deterministic simulation mode (access token not provided)",
            )
        return ProviderStatus(
            name=self.name,
            status="available",
            configured=True,
            message="Mapbox Access Token configured and active",
        )

    # -------------------------------------------------------------
    # High-Fidelity Deterministic Simulation Engine
    # -------------------------------------------------------------
    def _simulate_geocode(self, query: str, limit: int) -> List[GeocodingResult]:
        known_places = [
            ("charusat", 22.5996, 72.8205, "CHARUSAT, Changa, Gujarat, India"),
            ("changa", 22.6012, 72.8180, "Changa Village, Anand, Gujarat, India"),
            ("ahmedabad", 23.0225, 72.5714, "Ahmedabad, Gujarat, India"),
            ("gandhinagar", 23.2156, 72.6369, "Gandhinagar, Gujarat, India"),
            ("vadodara", 22.3072, 73.1812, "Vadodara, Gujarat, India"),
            ("airport", 23.0734, 72.6347, "SVP International Airport, Ahmedabad"),
        ]

        query_lower = query.lower().strip()
        matched: List[GeocodingResult] = []

        for name, lat, lng, addr in known_places:
            if name in query_lower or query_lower in name:
                matched.append(
                    GeocodingResult(
                        latitude=lat,
                        longitude=lng,
                        formatted_address=addr,
                        place_id=f"mapbox_place_{name}",
                        provider=self.name,
                        confidence=0.92,
                    )
                )

        if not matched:
            h = abs(hash(query))
            sim_lat = 22.1 + (h % 14000) / 10000.0
            sim_lng = 72.1 + ((h // 1000) % 14000) / 10000.0
            matched.append(
                GeocodingResult(
                    latitude=round(sim_lat, 6),
                    longitude=round(sim_lng, 6),
                    formatted_address=f"{query.title()}, Mapbox Region, India",
                    place_id=f"mapbox_sim_{h % 100000}",
                    provider=self.name,
                    confidence=0.82,
                )
            )

        return matched[:limit]

    def _simulate_reverse_geocode(self, lat: float, lng: float) -> GeocodingResult:
        dist_to_charusat = haversine_distance_meters(lat, lng, 22.5996, 72.8205)
        if dist_to_charusat < 1500:
            addr = "CHARUSAT Campus Road, Changa, Gujarat 388421"
        else:
            addr = f"Sector near {lat:.4f}, {lng:.4f}, Gujarat, India"

        return GeocodingResult(
            latitude=lat,
            longitude=lng,
            formatted_address=addr,
            place_id=f"mapbox_rev_{int(abs(lat*1000))}_{int(abs(lng*1000))}",
            provider=self.name,
            confidence=0.88,
        )

    def _simulate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: Any,
    ) -> RouteResult:
        mode_val = mode.value if hasattr(mode, "value") else str(mode)
        crow_flight_meters = haversine_distance_meters(origin_lat, origin_lng, dest_lat, dest_lng)
        road_distance_meters = int(round(crow_flight_meters * 1.28))

        speed_mps = estimate_speed_meters_per_sec(mode_val)
        base_duration_sec = int(round(road_distance_meters / speed_mps))

        if mode_val == "driving":
            traffic_delay_sec = int(round(base_duration_sec * 0.25))
        else:
            traffic_delay_sec = 0

        traffic_duration_sec = base_duration_sec + traffic_delay_sec
        congestion = calculate_congestion_level(traffic_delay_sec)

        mid_lat = (origin_lat + dest_lat) / 2.0 - 0.003
        mid_lng = (origin_lng + dest_lng) / 2.0 + 0.004
        points = [(origin_lat, origin_lng), (mid_lat, mid_lng), (dest_lat, dest_lng)]
        polyline = create_simple_encoded_polyline(points)

        return RouteResult(
            origin={"latitude": origin_lat, "longitude": origin_lng},
            destination={"latitude": dest_lat, "longitude": dest_lng},
            distance_meters=road_distance_meters,
            duration_seconds=base_duration_sec,
            traffic_duration_seconds=traffic_duration_sec,
            route_geometry=polyline,
            provider=self.name,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            travel_mode=mode_val,
            summary=RouteSummary(
                formatted_distance=format_distance_meters(road_distance_meters),
                formatted_duration=format_duration_seconds(traffic_duration_sec),
                formatted_traffic_delay=f"+{int(round(traffic_delay_sec / 60))} min" if traffic_delay_sec > 60 else "No delay",
                congestion_level=congestion,
            ),
            steps=[
                RouteStep(
                    instruction=f"Depart origin heading toward corridor ({mode_val})",
                    distance_meters=int(road_distance_meters * 0.5),
                    duration_seconds=int(traffic_duration_sec * 0.5),
                ),
                RouteStep(
                    instruction="Continue onto destination approach",
                    distance_meters=int(road_distance_meters * 0.5),
                    duration_seconds=int(traffic_duration_sec * 0.5),
                ),
            ],
        )

