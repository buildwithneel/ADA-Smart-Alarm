package com.thinkx.ada.domain.journey.model

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Validated geographical position fix with accuracy and time attributes.
 */
data class JourneyLocationFix(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float,
    val timestampEpochMs: Long,
    val speedMps: Float? = null,
    val bearingDegrees: Float? = null
) {
    init {
        require(latitude in -90.0..90.0) { "Latitude must be between -90 and 90 degrees: $latitude" }
        require(longitude in -180.0..180.0) { "Longitude must be between -180 and 180 degrees: $longitude" }
        require(accuracyMeters >= 0f) { "Accuracy must be non-negative: $accuracyMeters" }
    }

    /**
     * Determines whether the fix satisfies confidence criteria.
     * Rejects low-accuracy GPS readings (> [maxAccuracyMeters]), stale readings older than [maxAgeMs],
     * and clock drift fixes with timestamps in the future (> 5s ahead of [currentTimeMs]).
     */
    fun isReliable(
        maxAccuracyMeters: Float = 50f,
        maxAgeMs: Long = 60_000L,
        currentTimeMs: Long = System.currentTimeMillis()
    ): Boolean {
        if (accuracyMeters > maxAccuracyMeters) return false
        val age = currentTimeMs - timestampEpochMs
        if (age < -5_000L) return false // Fix timestamp significantly in the future
        if (age > maxAgeMs) return false // Fix is stale
        return true
    }

    /**
     * Computes the Great-Circle (Haversine) distance in meters to another coordinate.
     */
    fun distanceTo(targetLat: Double, targetLng: Double): Double {
        val earthRadiusMeters = 6_371_000.0
        val dLat = Math.toRadians(targetLat - latitude)
        val dLng = Math.toRadians(targetLng - longitude)
        val a = sin(dLat / 2) * sin(dLat / 2) +
                cos(Math.toRadians(latitude)) * cos(Math.toRadians(targetLat)) *
                sin(dLng / 2) * sin(dLng / 2)
        val c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return earthRadiusMeters * c
    }

    fun distanceTo(other: JourneyLocationFix): Double = distanceTo(other.latitude, other.longitude)
}
