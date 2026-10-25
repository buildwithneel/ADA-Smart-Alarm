package com.thinkx.ada.domain.model

import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Result model holding calculated schedule timestamps and metrics for ADA alarms.
 *
 * Implements the core ADA calculation rules:
 * - plannedArrivalTime = requiredArrivalTime - (safetyBuffer + weatherBuffer)
 * - recommendedLeaveTime = plannedArrivalTime - (travelDuration + trafficDelay)
 * - recommendedWakeTime = recommendedLeaveTime - preparationDuration
 */
data class CalculationResult(
    val requiredArrival: LocalDateTime,
    val plannedArrival: LocalDateTime,
    val recommendedLeaveTime: LocalDateTime,
    val recommendedWakeTime: LocalDateTime,
    val travelDurationMinutes: Int,
    val preparationDurationMinutes: Int,
    val safetyBufferMinutes: Int,
    val trafficDelayMinutes: Int = 0,
    val weatherBufferMinutes: Int = 0
) {
    val totalCommuteMinutes: Int
        get() = travelDurationMinutes + trafficDelayMinutes

    val totalBufferMinutes: Int
        get() = safetyBufferMinutes + weatherBufferMinutes

    val totalPreArrivalMinutes: Int
        get() = totalCommuteMinutes + totalBufferMinutes + preparationDurationMinutes

    /**
     * True if the wake-up time falls on the calendar day prior to the required arrival date.
     */
    val isOvernightWakeUp: Boolean
        get() = recommendedWakeTime.toLocalDate().isBefore(requiredArrival.toLocalDate())

    /**
     * True if the departure time falls on the calendar day prior to the required arrival date.
     */
    val isOvernightDeparture: Boolean
        get() = recommendedLeaveTime.toLocalDate().isBefore(requiredArrival.toLocalDate())

    val formattedRequiredArrival: String
        get() = formatTime(requiredArrival)

    val formattedPlannedArrival: String
        get() = formatTime(plannedArrival)

    val formattedRecommendedLeaveTime: String
        get() = formatTime(recommendedLeaveTime)

    val formattedRecommendedWakeTime: String
        get() = formatTime(recommendedWakeTime)

    companion object {
        private val TIME_FORMATTER = DateTimeFormatter.ofPattern("h:mm a", Locale.US)

        fun formatTime(dateTime: LocalDateTime): String = dateTime.format(TIME_FORMATTER)
    }
}
