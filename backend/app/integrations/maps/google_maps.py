from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.errors import NoRouteFoundException, ProviderException
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

logger = logging.getLogger("ada.maps.google")


class GoogleMapsProvider(MapProviderInterface):
    """
    Google Maps Platform implementation:
    - Geocoding API (Forward & Reverse)
    - Directions API (Traffic-aware routes with duration_in_traffic)
    - Offline fallback simulation when API key is unconfigured
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        self.timeout = settings.PROVIDER_TIMEOUT_SECONDS

    @property
    def name(self) -> str:
        return "google"

    async def geocode(self, query: str, limit: int = 5) -> List[GeocodingResult]:
        if not self.api_key:
            return self._simulate_geocode(query, limit)

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": query, "key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    raise ProviderException(
                        f"Google Geocoding HTTP {resp.status_code}",
                        provider=self.name,
                    )
                data = resp.json()

            status = data.get("status")
            if status == "ZERO_RESULTS":
                return []
            elif status == "OVER_QUERY_LIMIT":
                raise ProviderException("Google Maps quota exceeded", provider=self.name)
            elif status == "REQUEST_DENIED":
                raise ProviderException("Google Maps API key invalid or unauthorized", provider=self.name)
            elif status != "OK":
                raise ProviderException(f"Google Maps status: {status}", provider=self.name)

            results: List[GeocodingResult] = []
            for item in data.get("results", [])[:limit]:
                loc = item["geometry"]["location"]
                results.append(
                    GeocodingResult(
                        latitude=loc["lat"],
                        longitude=loc["lng"],
                        formatted_address=item.get("formatted_address", query),
                        place_id=item.get("place_id"),
                        provider=self.name,
                        confidence=1.0,
                    )
                )
            return results

        except httpx.TimeoutException:
            raise ProviderException("Google Geocoding timeout", provider=self.name)
        except httpx.RequestError as e:
            raise ProviderException(f"Google Geocoding network error: {str(e)}", provider=self.name)

    async def reverse_geocode(self, lat: float, lng: float) -> Optional[GeocodingResult]:
        if not self.api_key:
            return self._simulate_reverse_geocode(lat, lng)

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"latlng": f"{lat},{lng}", "key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    raise ProviderException(
                        f"Google Reverse Geocoding HTTP {resp.status_code}",
                        provider=self.name,
                    )
                data = resp.json()

            status = data.get("status")
            if status == "ZERO_RESULTS":
                return None
            elif status != "OK":
                raise ProviderException(f"Google Maps status: {status}", provider=self.name)

            first = data.get("results", [])[0]
            loc = first["geometry"]["location"]
            return GeocodingResult(
                latitude=loc["lat"],
                longitude=loc["lng"],
                formatted_address=first.get("formatted_address", f"{lat:.4f}, {lng:.4f}"),
                place_id=first.get("place_id"),
                provider=self.name,
                confidence=1.0,
            )
        except httpx.TimeoutException:
            raise ProviderException("Google Reverse Geocoding timeout", provider=self.name)
        except httpx.RequestError as e:
            raise ProviderException(f"Google Reverse Geocoding network error: {str(e)}", provider=self.name)

    async def calculate_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: TravelMode = TravelMode.DRIVING,
        departure_time: Optional[int] = None,
    ) -> RouteResult:
        if not self.api_key:
            return self._simulate_route(origin_lat, origin_lng, dest_lat, dest_lng, mode)

        google_mode_map = {
            TravelMode.DRIVING: "driving",
            TravelMode.WALKING: "walking",
            TravelMode.CYCLING: "bicycling",
            TravelMode.TRANSIT: "transit",
        }
        g_mode = google_mode_map.get(mode, "driving")

        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": f"{origin_lat},{origin_lng}",
            "destination": f"{dest_lat},{dest_lng}",
            "mode": g_mode,
            "departure_time": departure_time or "now",
            "key": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    raise ProviderException(
                        f"Google Directions HTTP {resp.status_code}",
                        provider=self.name,
                    )
                data = resp.json()

            status = data.get("status")
            if status == "ZERO_RESULTS" or status == "NOT_FOUND":
                raise NoRouteFoundException()
            elif status == "OVER_QUERY_LIMIT":
                raise ProviderException("Google Maps quota exceeded", provider=self.name)
            elif status != "OK":
                raise ProviderException(f"Google Directions status: {status}", provider=self.name)

            route = data["routes"][0]
            leg = route["legs"][0]

            dist_meters = leg["distance"]["value"]
            duration_sec = leg["duration"]["value"]
            # Traffic-aware duration if present, else fallback to standard duration
            traffic_sec = leg.get("duration_in_traffic", {}).get("value", duration_sec)
            traffic_delay = max(0, traffic_sec - duration_sec)
            congestion = calculate_congestion_level(traffic_delay)

            steps: List[RouteStep] = []
            for s in leg.get("steps", []):
                steps.append(
                    RouteStep(
                        instruction=s.get("html_instructions", "").replace("<b>", "").replace("</b>", " "),
                        distance_meters=s.get("distance", {}).get("value", 0),
                        duration_seconds=s.get("duration", {}).get("value", 0),
                    )
                )

            has_traffic = "duration_in_traffic" in leg
            return RouteResult(
                origin={"latitude": origin_lat, "longitude": origin_lng},
                destination={"latitude": dest_lat, "longitude": dest_lng},
                distance_meters=dist_meters,
                duration_seconds=duration_sec,
                traffic_duration_seconds=traffic_sec,
                route_geometry=route.get("overview_polyline", {}).get("points", ""),
                provider=self.name,
                is_traffic_aware=has_traffic,
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
            raise ProviderException(f"Google Directions network error: {str(e)}", provider=self.name)

    async def check_health(self) -> ProviderStatus:
        if not self.api_key:
            return ProviderStatus(
                name=self.name,
                status="available",
                configured=False,
                message="Google Maps running in offline deterministic simulation mode (API key not provided)",
            )
        return ProviderStatus(
            name=self.name,
            status="available",
            configured=True,
            message="Google Maps Platform key configured and active",
        )

    # -------------------------------------------------------------
    # High-Fidelity Deterministic Simulation Engine
    # -------------------------------------------------------------
    def _simulate_geocode(self, query: str, limit: int) -> List[GeocodingResult]:
        known_places = [
            ("charusat", 22.5996, 72.8205, "CHARUSAT University, Highway 188, Changa, Gujarat 388421"),
            ("changa", 22.6012, 72.8180, "Changa, Petlad Taluka, Anand District, Gujarat"),
            ("ahmedabad", 23.0225, 72.5714, "Ahmedabad, Gujarat, India"),
            ("gandhinagar", 23.2156, 72.6369, "Gandhinagar, Capital of Gujarat, India"),
            ("vadodara", 22.3072, 73.1812, "Vadodara, Gujarat, India"),
            ("airport", 23.0734, 72.6347, "Sardar Vallabhbhai Patel International Airport (AMD), Ahmedabad"),
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
                        place_id=f"google_place_{name}",
                        provider=self.name,
                        confidence=0.95,
                    )
                )

        if not matched:
            # Deterministic coordinate hash for arbitrary queries
            h = abs(hash(query))
            sim_lat = 22.0 + (h % 15000) / 10000.0
            sim_lng = 72.0 + ((h // 1000) % 15000) / 10000.0
            matched.append(
                GeocodingResult(
                    latitude=round(sim_lat, 6),
                    longitude=round(sim_lng, 6),
                    formatted_address=f"{query.title()}, Gujarat, India",
                    place_id=f"google_sim_{h % 100000}",
                    provider=self.name,
                    confidence=0.85,
                )
            )

        return matched[:limit]

    def _simulate_reverse_geocode(self, lat: float, lng: float) -> GeocodingResult:
        dist_to_charusat = haversine_distance_meters(lat, lng, 22.5996, 72.8205)
        if dist_to_charusat < 1500:
            addr = "Near CHARUSAT Campus, Changa, Anand, Gujarat 388421"
        else:
            addr = f"Roadway near {lat:.4f}° N, {lng:.4f}° E, Gujarat, India"

        return GeocodingResult(
            latitude=lat,
            longitude=lng,
            formatted_address=addr,
            place_id=f"google_rev_{int(abs(lat*1000))}_{int(abs(lng*1000))}",
            provider=self.name,
            confidence=0.9,
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
        # Real roads have a curvature/detour factor (~1.25)
        road_distance_meters = int(round(crow_flight_meters * 1.25))

        speed_mps = estimate_speed_meters_per_sec(mode_val)
        base_duration_sec = int(round(road_distance_meters / speed_mps))

        # Driving traffic simulation (adds 15-30% depending on distance)
        if mode_val == "driving":
            traffic_delay_sec = int(round(base_duration_sec * 0.22))
        else:
            traffic_delay_sec = 0

        traffic_duration_sec = base_duration_sec + traffic_delay_sec
        congestion = calculate_congestion_level(traffic_delay_sec)

        # Generate polyline connecting origin, waypoint, and destination
        mid_lat = (origin_lat + dest_lat) / 2.0 + 0.005
        mid_lng = (origin_lng + dest_lng) / 2.0 - 0.005
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
            is_traffic_aware=False,
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
                    instruction=f"Start toward destination via main arterial road ({mode_val})",
                    distance_meters=int(road_distance_meters * 0.4),
                    duration_seconds=int(traffic_duration_sec * 0.4),
                ),
                RouteStep(
                    instruction="Arrive at final destination entrance",
                    distance_meters=int(road_distance_meters * 0.6),
                    duration_seconds=int(traffic_duration_sec * 0.6),
                ),
            ],
        )

