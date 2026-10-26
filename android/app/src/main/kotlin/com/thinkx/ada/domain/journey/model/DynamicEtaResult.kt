package com.thinkx.ada.domain.journey.model

enum class EtaSource {
    TRAFFIC_AWARE_PROVIDER,
    NON_TRAFFIC_FALLBACK,
    UNAVAILABLE
}

/**
 * Encapsulates a dynamically computed Estimated Time of Arrival (ETA).
 */
data class DynamicEtaResult(
    val predictedArrivalEpochMs: Long,
    val remainingDurationSeconds: Int,
    val remainingDistanceMeters: Int,
    val isTrafficAware: Boolean,
    val source: EtaSource,
    val providerName: String,
    val lastRefreshEpochMs: Long,
    val isStale: Boolean = false,
    val routeGeometry: String? = null
) {
    init {
        require(remainingDurationSeconds >= 0) { "Remaining duration must be non-negative: $remainingDurationSeconds" }
        require(remainingDistanceMeters >= 0) { "Remaining distance must be non-negative: $remainingDistanceMeters" }
    }

    /**
     * Checks if this ETA reading is considered stale relative to [nowEpochMs]
     * based on the maximum freshness window [stalenessThresholdMs] (default 5 minutes).
     */
    fun checkStaleness(nowEpochMs: Long, stalenessThresholdMs: Long = 300_000L): DynamicEtaResult {
        val stale = (nowEpochMs - lastRefreshEpochMs) > stalenessThresholdMs
        return if (stale != isStale) copy(isStale = stale) else this
    }
}
