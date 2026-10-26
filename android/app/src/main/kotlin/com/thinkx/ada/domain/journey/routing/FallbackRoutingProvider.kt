package com.thinkx.ada.domain.journey.routing

import com.thinkx.ada.domain.journey.model.JourneyLocationFix
import kotlin.math.roundToInt

/**
 * Deterministic, offline-first fallback routing provider using Great-Circle distance
 * and a standard driving velocity estimate (40 km/h = ~11.11 m/s).
 *
 * Guaranteed to operate without internet connection or external API keys.
 * Clearly identified as non-traffic-aware.
 */
class FallbackRoutingProvider(
    private val averageSpeedMps: Double = 11.11
) : RoutingProvider {

    override val name: String = "Offline Fallback (Non-Traffic)"

    override suspend fun calculateRoute(request: RouteRequest): Result<RouteResult> {
        val originFix = JourneyLocationFix(
            latitude = request.originLat,
            longitude = request.originLng,
            accuracyMeters = 10f,
            timestampEpochMs = System.currentTimeMillis()
        )

        val distanceMeters = originFix.distanceTo(request.destinationLat, request.destinationLng).roundToInt()
        val durationSeconds = if (distanceMeters > 0 && averageSpeedMps > 0) {
            (distanceMeters / averageSpeedMps).roundToInt()
        } else {
            0
        }

        return Result.success(
            RouteResult(
                distanceMeters = distanceMeters,
                baseDurationSeconds = durationSeconds,
                trafficDurationSeconds = durationSeconds,
                routeGeometry = "",
                providerName = name,
                isTrafficAware = false,
                congestionLevel = "unknown"
            )
        )
    }
}
