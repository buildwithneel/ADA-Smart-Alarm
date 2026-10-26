package com.thinkx.ada.domain.journey.model

/**
 * Domain model representing the scheduling parameters for a journey.
 *
 * All timestamps are in canonical UTC Epoch Milliseconds.
 * The scheduled departure time serves as the anchor for initiating tracking preparation.
 */
data class JourneySchedule(
    val scheduledDepartureEpochMs: Long,
    val trackingLeadMinutes: Int = 15,
    val approachingThresholdMeters: Int = 1000,
    val arrivalThresholdMeters: Int = 100
) {
    init {
        require(trackingLeadMinutes >= 0) { "Tracking lead minutes must be non-negative" }
        require(approachingThresholdMeters > arrivalThresholdMeters) {
            "Approaching threshold ($approachingThresholdMeters m) must exceed arrival threshold ($arrivalThresholdMeters m)"
        }
        require(arrivalThresholdMeters > 0) { "Arrival threshold must be strictly positive" }
    }

    /**
     * Exact UTC epoch millisecond when ADA should prepare and begin monitoring the journey.
     */
    val trackingStartEpochMs: Long
        get() = scheduledDepartureEpochMs - (trackingLeadMinutes * 60 * 1000L)

    /**
     * Checks whether the tracking start time has been reached or passed relative to [nowEpochMs].
     */
    fun isTrackingStartDue(nowEpochMs: Long): Boolean = nowEpochMs >= trackingStartEpochMs
}
