package com.thinkx.ada.domain.journey.engine

import com.thinkx.ada.domain.journey.model.DynamicEtaResult
import com.thinkx.ada.domain.journey.model.EtaSource
import com.thinkx.ada.domain.journey.model.JourneyLocationFix
import com.thinkx.ada.domain.journey.routing.RouteResult
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Pure Kotlin Mathematical Calculation Engine for Dynamic Journey Monitoring & ETA Tracking.
 *
 * Implements ADA's destination-aware dynamic ETA contract:
 * 1. Tracking start calculation from scheduled departure and lead time.
 * 2. GPS accuracy filtering, staleness rejection, and velocity jump protection.
 * 3. Traffic-aware ETA derivation where elapsed time is never double-counted,
 *    and no artificial stop penalties are added on top of provider traffic duration.
 * 4. Fallback ETA derivation with explicit non-traffic labeling.
 * 5. Route deviation detection against route corridors.
 * 6. Idempotent proximity alert triggers (Approaching threshold: 1,000m, Arrival threshold: 100m).
 */
object DynamicEtaEngine {

    const val DEFAULT_TRACKING_LEAD_MINUTES = 15
    const val DEFAULT_APPROACHING_THRESHOLD_METERS = 1000
    const val DEFAULT_ARRIVAL_THRESHOLD_METERS = 100

    /**
     * Calculates the exact tracking start epoch ms given scheduled departure and lead time.
     */
    fun calculateTrackingStartTime(
        scheduledDepartureEpochMs: Long,
        trackingLeadMinutes: Int = DEFAULT_TRACKING_LEAD_MINUTES
    ): Long {
        require(trackingLeadMinutes >= 0) { "Tracking lead time must be non-negative" }
        return scheduledDepartureEpochMs - (trackingLeadMinutes * 60 * 1000L)
    }

    /**
     * Filters out unreliable location fixes based on accuracy, age, and future timestamps.
     */
    fun isLocationFixValid(
        fix: JourneyLocationFix,
        maxAccuracyMeters: Float = 50f,
        maxAgeMs: Long = 60_000L,
        currentTimeMs: Long = System.currentTimeMillis()
    ): Boolean {
        return fix.isReliable(maxAccuracyMeters, maxAgeMs, currentTimeMs)
    }

    /**
     * Detects unrealistic GPS position jumps between consecutive location fixes.
     * Rejects jumps exceeding [maxRealisticSpeedMps] (default ~162 km/h) unless accuracy is exceptionally high.
     */
    fun isGpsJump(
        previousFix: JourneyLocationFix,
        currentFix: JourneyLocationFix,
        maxRealisticSpeedMps: Float = 45f
    ): Boolean {
        val elapsedSec = (currentFix.timestampEpochMs - previousFix.timestampEpochMs) / 1000.0
        if (elapsedSec <= 0.5) return false

        val distanceMeters = previousFix.distanceTo(currentFix)
        val impliedSpeedMps = distanceMeters / elapsedSec

        // If implied speed is absurdly high and accuracy is not pin-point, flag as GPS jump
        return impliedSpeedMps > maxRealisticSpeedMps && currentFix.accuracyMeters > 15f
    }

    /**
     * Derives a dynamic ETA from a routing provider's result.
     *
     * Invariants:
     * - The duration from the routing provider is the remaining duration from current position to destination.
     * - Predicted arrival = fix.timestampEpochMs + (durationSeconds * 1000L).
     * - Elapsed travel time is NOT added twice.
     * - No artificial stop penalty is added on top of a traffic-aware duration.
     */
    fun calculateEtaFromProvider(
        fix: JourneyLocationFix,
        routeResult: RouteResult,
        currentTimeEpochMs: Long = System.currentTimeMillis()
    ): DynamicEtaResult {
        val durationSeconds = if (routeResult.isTrafficAware && routeResult.trafficDurationSeconds > 0) {
            routeResult.trafficDurationSeconds
        } else {
            routeResult.baseDurationSeconds
        }

        val predictedArrivalEpochMs = fix.timestampEpochMs + (durationSeconds * 1000L)

        return DynamicEtaResult(
            predictedArrivalEpochMs = predictedArrivalEpochMs,
            remainingDurationSeconds = durationSeconds,
            remainingDistanceMeters = routeResult.distanceMeters,
            isTrafficAware = routeResult.isTrafficAware,
            source = if (routeResult.isTrafficAware) EtaSource.TRAFFIC_AWARE_PROVIDER else EtaSource.NON_TRAFFIC_FALLBACK,
            providerName = routeResult.providerName,
            lastRefreshEpochMs = currentTimeEpochMs,
            isStale = false,
            routeGeometry = routeResult.routeGeometry
        )
    }

    /**
     * Computes a conservative non-traffic fallback ETA using Great-Circle distance
     * and a realistic urban/suburban average velocity (default 40 km/h = ~11.11 m/s).
     *
     * Explicitly marked as non-traffic-aware.
     */
    fun calculateFallbackEta(
        fix: JourneyLocationFix,
        destinationLat: Double,
        destinationLng: Double,
        averageSpeedMps: Double = 11.11,
        currentTimeEpochMs: Long = System.currentTimeMillis()
    ): DynamicEtaResult {
        val distanceMeters = fix.distanceTo(destinationLat, destinationLng).roundToInt()
        val durationSeconds = if (distanceMeters > 0 && averageSpeedMps > 0) {
            (distanceMeters / averageSpeedMps).roundToInt()
        } else {
            0
        }

        val predictedArrivalEpochMs = fix.timestampEpochMs + (durationSeconds * 1000L)

        return DynamicEtaResult(
            predictedArrivalEpochMs = predictedArrivalEpochMs,
            remainingDurationSeconds = durationSeconds,
            remainingDistanceMeters = distanceMeters,
            isTrafficAware = false,
            source = EtaSource.NON_TRAFFIC_FALLBACK,
            providerName = "Fallback Heuristic",
            lastRefreshEpochMs = currentTimeEpochMs,
            isStale = false
        )
    }

    /**
     * Determines whether an updated route calculation should be dispatched to the provider.
     * Uses throttling and hysteresis to prevent excessive API calls and jitter:
     * - Recalculates immediately if confirmed route deviation is detected.
     * - Disallows requests if minimum cooldown (30s) hasn't passed since last request.
     * - Recalculates if user has progressed >= [minDistanceDeltaMeters] AND >= [minIntervalSec] elapsed.
     * - Recalculates if current ETA is stale (> [stalenessThresholdMs]).
     */
    fun shouldRecalculateRoute(
        isDeviated: Boolean,
        lastRequestEpochMs: Long,
        lastLocationFix: JourneyLocationFix?,
        currentFix: JourneyLocationFix,
        currentTimeEpochMs: Long = System.currentTimeMillis(),
        minDistanceDeltaMeters: Double = 200.0,
        minIntervalSec: Long = 180L,
        stalenessThresholdMs: Long = 300_000L
    ): Boolean {
        val elapsedSinceLastRequestMs = currentTimeEpochMs - lastRequestEpochMs

        // Never request faster than 30s to respect provider rate limits
        if (elapsedSinceLastRequestMs < 30_000L) return false

        // Immediate recalculation upon confirmed route deviation
        if (isDeviated) return true

        // Recalculate if previous result is stale
        if (elapsedSinceLastRequestMs >= stalenessThresholdMs) return true

        // Check progress thresholds: distance moved and time elapsed
        val distanceMoved = lastLocationFix?.distanceTo(currentFix) ?: Double.MAX_VALUE
        val timeElapsedSec = elapsedSinceLastRequestMs / 1000L

        return distanceMoved >= minDistanceDeltaMeters && timeElapsedSec >= minIntervalSec
    }

    /**
     * Evaluates whether the user's position deviates from the expected route geometry.
     * Computes the minimum distance from [currentFix] to route polyline points.
     * If the closest distance exceeds [deviationThresholdMeters] (default 250m), triggers deviation.
     */
    fun isRouteDeviation(
        currentFix: JourneyLocationFix,
        routePoints: List<Pair<Double, Double>>,
        deviationThresholdMeters: Double = 250.0
    ): Boolean {
        if (routePoints.isEmpty()) return false

        var minDistance = Double.MAX_VALUE
        for (pt in routePoints) {
            val dist = currentFix.distanceTo(pt.first, pt.second)
            if (dist < minDistance) {
                minDistance = dist
            }
        }

        return minDistance > deviationThresholdMeters
    }

    /**
     * Checks if the approaching destination alert condition is met.
     * Idempotent: triggers only once per journey.
     */
    fun checkApproachingAlert(
        currentDistanceMeters: Int,
        approachingThresholdMeters: Int = DEFAULT_APPROACHING_THRESHOLD_METERS,
        alreadyAlerted: Boolean = false
    ): Boolean {
        if (alreadyAlerted) return false
        return currentDistanceMeters <= approachingThresholdMeters
    }

    /**
     * Checks if arrival at the destination is confirmed.
     * Requires:
     * 1. Distance <= arrivalThresholdMeters (default 100m).
     * 2. Good GPS accuracy (<= 50m).
     * 3. Multi-fix confirmation count >= requiredConfirmations (prevents single-fix false arrival).
     */
    fun checkArrivalConfirmation(
        currentDistanceMeters: Int,
        accuracyMeters: Float,
        arrivalThresholdMeters: Int = DEFAULT_ARRIVAL_THRESHOLD_METERS,
        consecutiveConfirmations: Int = 1,
        requiredConfirmations: Int = 2
    ): Boolean {
        if (accuracyMeters > 50f) return false // Inaccurate fix cannot confirm arrival
        return currentDistanceMeters <= arrivalThresholdMeters && consecutiveConfirmations >= requiredConfirmations
    }

    /**
     * Helper to decode an encoded Google Polyline into a list of (latitude, longitude) coordinates.
     */
    fun decodePolyline(encoded: String): List<Pair<Double, Double>> {
        val poly = mutableListOf<Pair<Double, Double>>()
        var index = 0
        val len = encoded.length
        var lat = 0
        var lng = 0

        while (index < len) {
            var b: Int
            var shift = 0
            var result = 0
            do {
                b = encoded[index++].code - 63
                result = result or (b and 0x1f shl shift)
                shift += 5
            } while (b >= 0x20)
            val dlat = if (result and 1 != 0) (result shr 1).inv() else result shr 1
            lat += dlat

            shift = 0
            result = 0
            do {
                b = encoded[index++].code - 63
                result = result or (b and 0x1f shl shift)
                shift += 5
            } while (b >= 0x20)
            val dlng = if (result and 1 != 0) (result shr 1).inv() else result shr 1
            lng += dlng

            poly.add(Pair(lat / 1E5, lng / 1E5))
        }

        return poly
    }
}
