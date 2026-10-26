package com.thinkx.ada.domain.journey.model

enum class JourneyState {
    SCHEDULED,
    TRACKING_PENDING,
    ACTIVE_TRACKING,
    TRACKING_DEGRADED,
    RECALCULATING,
    APPROACHING,
    ARRIVED,
    STOPPED,
    CANCELLED,
    FAILED;

    val isTrackingActive: Boolean
        get() = this in setOf(ACTIVE_TRACKING, TRACKING_DEGRADED, RECALCULATING, APPROACHING)

    val isTerminal: Boolean
        get() = this in setOf(ARRIVED, STOPPED, CANCELLED, FAILED)
}

enum class JourneyAlertEvent {
    APPROACHING_ALERT,
    ARRIVAL_CONFIRMED
}
