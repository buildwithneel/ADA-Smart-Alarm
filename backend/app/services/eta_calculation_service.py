"""
ADA ETA Calculation Service — Application Layer Orchestrator.

Coordinates between:
1. RoutingService (get live route durations from Google/Mapbox)
2. ETACalculationEngine (pure domain math)
3. AlarmRepository (persist computed wake/leave times back to alarm)

This service is the single entry point for all ETA calculation workflows.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.models.alarm import Alarm
from app.repositories.alarm_repository import AlarmRepository
from app.schemas.eta import (
    AlarmETAUpdateResult,
    ETACalculateRequest,
    ETACalculateResponse,
    ETAPreviewRequest,
    ETAPreviewResponse,
)
from app.schemas.location import TravelMode
from app.services.eta_engine import (
    CONFIDENCE_GOOGLE_LIVE,
    CONFIDENCE_HEURISTIC,
    CONFIDENCE_MAPBOX_LIVE,
    ETACalculationEngine,
)
from app.services.routing_service import RoutingService

logger = logging.getLogger("ada.services.eta")


class ETACalculationService:
    """
    Application service orchestrating ETA calculations for ADA alarms.

    Two main workflows:
    1. calculate(request) — full ETA with live routing, for preview and on-demand use
    2. evaluate_alarm(alarm) — fetch live route + calculate + persist result into alarm record
    """

    def __init__(
        self,
        routing_service: RoutingService,
        alarm_repo: Optional[AlarmRepository] = None,
    ):
        self.routing_service = routing_service
        self.alarm_repo = alarm_repo

    # ------------------------------------------------------------------
    # Full ETA Calculation (for API endpoint)
    # ------------------------------------------------------------------

    async def calculate(self, request: ETACalculateRequest) -> ETACalculateResponse:
        """
        Full ETA calculation: fetch live route, run ETA engine, return full response.

        If override durations are provided in the request (client already calculated
        the route), skip the backend routing call for efficiency.
        """
        # 1. Use overrides if provided (avoids redundant routing API call)
        if (
            request.override_base_duration_seconds is not None
            and request.override_traffic_duration_seconds is not None
        ):
            base_secs = request.override_base_duration_seconds
            traffic_secs = request.override_traffic_duration_seconds
            data_source = "client_provided"
            confidence = CONFIDENCE_GOOGLE_LIVE  # Assume client used a real provider
            distance_km = None

            logger.debug(
                "ETA calculation using client-provided route durations "
                f"(base={base_secs}s, traffic={traffic_secs}s)"
            )
        else:
            # 2. Fetch live route from routing provider
            try:
                travel_mode = self._map_transport_mode(request.transport_mode.value)
                route = await self.routing_service.calculate_route(
                    origin_lat=request.origin_lat,
                    origin_lng=request.origin_lng,
                    dest_lat=request.dest_lat,
                    dest_lng=request.dest_lng,
                    mode=travel_mode,
                )
                base_secs = route.duration_seconds
                traffic_secs = route.traffic_duration_seconds
                distance_km = round(route.distance_meters / 1000, 2)
                data_source = route.provider

                # Assign confidence by provider
                if route.provider == "google":
                    confidence = CONFIDENCE_GOOGLE_LIVE
                elif route.provider == "mapbox":
                    confidence = CONFIDENCE_MAPBOX_LIVE
                else:
                    confidence = CONFIDENCE_HEURISTIC

                logger.info(
                    f"ETA: live route from {data_source} "
                    f"(base={base_secs}s, traffic={traffic_secs}s, dist={distance_km}km)"
                )

            except Exception as exc:
                # Fall back to Haversine heuristic
                logger.warning(f"Routing provider failed, using heuristic fallback: {exc}")
                base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
                    request.origin_lat,
                    request.origin_lng,
                    request.dest_lat,
                    request.dest_lng,
                    request.transport_mode,
                )
                data_source = "heuristic"
                confidence = CONFIDENCE_HEURISTIC
                distance_km = None

        # 3. Run the pure ETA engine
        result = ETACalculationEngine.calculate(
            request=request,
            base_duration_seconds=base_secs,
            traffic_duration_seconds=traffic_secs,
            distance_km=distance_km,
            data_source=data_source,
            provider_confidence=confidence,
        )

        return result

    # ------------------------------------------------------------------
    # Lightweight Preview (for form live-update)
    # ------------------------------------------------------------------

    async def calculate_preview(self, request: ETAPreviewRequest) -> ETAPreviewResponse:
        """
        Lightweight preview calculation. Used for real-time form updates.
        Accepts optional pre-computed route durations to skip API call.
        """
        if (
            request.base_duration_seconds is not None
            and request.traffic_duration_seconds is not None
        ):
            base_secs = request.base_duration_seconds
            traffic_secs = request.traffic_duration_seconds
            data_source = "client_route"
            confidence = CONFIDENCE_GOOGLE_LIVE
        else:
            try:
                travel_mode = self._map_transport_mode(request.transport_mode.value)
                route = await self.routing_service.calculate_route(
                    origin_lat=request.origin_lat,
                    origin_lng=request.origin_lng,
                    dest_lat=request.dest_lat,
                    dest_lng=request.dest_lng,
                    mode=travel_mode,
                )
                base_secs = route.duration_seconds
                traffic_secs = route.traffic_duration_seconds
                data_source = route.provider
                confidence = (
                    CONFIDENCE_GOOGLE_LIVE
                    if route.provider == "google"
                    else CONFIDENCE_MAPBOX_LIVE
                )
            except Exception as exc:
                logger.warning(f"Preview routing failed, using heuristic: {exc}")
                base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
                    request.origin_lat,
                    request.origin_lng,
                    request.dest_lat,
                    request.dest_lng,
                    request.transport_mode,
                )
                data_source = "heuristic"
                confidence = CONFIDENCE_HEURISTIC

        return ETACalculationEngine.calculate_preview(
            request=request,
            base_duration_seconds=base_secs,
            traffic_duration_seconds=traffic_secs,
            data_source=data_source,
            provider_confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Alarm ETA Re-evaluation (for persisting back to alarm record)
    # ------------------------------------------------------------------

    async def evaluate_alarm(self, alarm: Alarm) -> AlarmETAUpdateResult:
        """
        Re-evaluate ETA for a specific Alarm and persist results to the database.

        Called by:
        - The /eta/alarms/{alarm_id}/evaluate endpoint
        - Celery background workers (future)

        Steps:
        1. Get destination coordinates from alarm.destination
        2. Origin defaults to destination for self-evaluation (Celery will supply live GPS)
        3. Compute ETA using standard calculation
        4. Persist calculated_wake_time, calculated_leave_time, travel_minutes to alarm model
        """
        if not self.alarm_repo:
            raise RuntimeError("AlarmRepository is required for alarm ETA evaluation")

        destination = alarm.destination
        if not destination:
            raise ValueError(f"Alarm {alarm.id} has no linked destination")

        # Use hardcoded origin = destination for server-side (Celery will have real GPS)
        origin_lat = destination.latitude
        origin_lng = destination.longitude
        dest_lat = destination.latitude
        dest_lng = destination.longitude

        from app.models.alarm import TransportMode as ModelTransportMode
        from app.schemas.eta import ETACalculateRequest as SchemaRequest

        mode_map = {
            ModelTransportMode.DRIVING: "driving",
            ModelTransportMode.TRANSIT: "transit",
            ModelTransportMode.BICYCLING: "bicycling",
            ModelTransportMode.WALKING: "walking",
        }

        arrival_str = alarm.arrival_time.strftime("%H:%M")

        try:
            travel_mode = self._map_transport_mode(alarm.transportation_mode.value)
            route = await self.routing_service.calculate_route(
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                dest_lat=dest_lat,
                dest_lng=dest_lng,
                mode=travel_mode,
            )
            base_secs = route.duration_seconds
            traffic_secs = route.traffic_duration_seconds
            data_source = route.provider
            confidence = (
                CONFIDENCE_GOOGLE_LIVE
                if route.provider == "google"
                else CONFIDENCE_MAPBOX_LIVE
            )
        except Exception as exc:
            logger.warning(f"Alarm {alarm.id} routing failed, using heuristic: {exc}")
            base_secs, traffic_secs = ETACalculationEngine.calculate_heuristic_duration(
                origin_lat, origin_lng, dest_lat, dest_lng,
                alarm.transportation_mode,
            )
            data_source = "heuristic"
            confidence = CONFIDENCE_HEURISTIC

        from app.schemas.eta import ETACalculateRequest as Req
        from app.models.alarm import TransportMode as TM

        req = Req(
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            desired_arrival_time=arrival_str,
            preparation_time_minutes=alarm.preparation_time,
            safety_buffer_minutes=alarm.safety_buffer,
            transport_mode=alarm.transportation_mode,
        )

        result = ETACalculationEngine.calculate(
            request=req,
            base_duration_seconds=base_secs,
            traffic_duration_seconds=traffic_secs,
            data_source=data_source,
            provider_confidence=confidence,
        )

        # Parse ISO strings back to datetime for DB storage
        from datetime import datetime
        wake_dt = datetime.fromisoformat(result.wake_time_iso)
        leave_dt = datetime.fromisoformat(result.leave_time_iso)

        # Persist to alarm record
        updated = self.alarm_repo.update_eta_fields(
            alarm=alarm,
            calculated_wake_time=wake_dt,
            calculated_leave_time=leave_dt,
            current_travel_minutes=result.total_travel_minutes,
            traffic_delay_minutes=result.breakdown.traffic_delay_minutes,
        )

        now = datetime.now(tz=timezone.utc)

        return AlarmETAUpdateResult(
            alarm_id=str(alarm.id),
            calculated_wake_time=updated.calculated_wake_time,
            calculated_leave_time=updated.calculated_leave_time,
            current_travel_minutes=updated.current_travel_minutes or 0,
            traffic_delay_minutes=updated.traffic_delay_minutes or 0,
            last_evaluated_at=updated.last_evaluated_at or now,
            confidence_score=result.breakdown.confidence_score,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_transport_mode(mode_str: str) -> TravelMode:
        """Map TransportMode enum value to TravelMode enum used by RoutingService."""
        from app.schemas.location import TravelMode
        mapping = {
            "driving": TravelMode.DRIVING,
            "walking": TravelMode.WALKING,
            "bicycling": TravelMode.CYCLING,
            "cycling": TravelMode.CYCLING,
            "transit": TravelMode.TRANSIT,
        }
        return mapping.get(mode_str.lower(), TravelMode.DRIVING)
