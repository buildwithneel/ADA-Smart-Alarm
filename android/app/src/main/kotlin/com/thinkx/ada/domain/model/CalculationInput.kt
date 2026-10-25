package com.thinkx.ada.domain.model

import java.time.LocalDateTime

/**
 * Immutable input parameter model for ADA alarm schedule calculation.
 *
 * @property requiredArrival The non-negotiable target arrival deadline at the destination.
 * @property travelDurationMinutes Base estimated transit duration in minutes.
 * @property preparationDurationMinutes User's required morning routine duration in minutes.
 * @property safetyBufferMinutes User-configured safety buffer cushion in minutes.
 * @property trafficDelayMinutes Dynamic delay caused by congestion in minutes (default 0).
 * @property weatherBufferMinutes Dynamic delay caused by adverse weather conditions in minutes (default 0).
 */
data class CalculationInput(
    val requiredArrival: LocalDateTime,
    val travelDurationMinutes: Int,
    val preparationDurationMinutes: Int,
    val safetyBufferMinutes: Int,
    val trafficDelayMinutes: Int = 0,
    val weatherBufferMinutes: Int = 0
) {
    init {
        require(travelDurationMinutes >= 0) { "Travel duration cannot be negative: $travelDurationMinutes" }
        require(preparationDurationMinutes >= 0) { "Preparation duration cannot be negative: $preparationDurationMinutes" }
        require(safetyBufferMinutes >= 0) { "Safety buffer cannot be negative: $safetyBufferMinutes" }
        require(trafficDelayMinutes >= 0) { "Traffic delay cannot be negative: $trafficDelayMinutes" }
        require(weatherBufferMinutes >= 0) { "Weather buffer cannot be negative: $weatherBufferMinutes" }
    }
}
