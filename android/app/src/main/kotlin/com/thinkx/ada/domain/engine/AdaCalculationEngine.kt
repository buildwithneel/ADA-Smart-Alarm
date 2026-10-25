package com.thinkx.ada.domain.engine

import com.thinkx.ada.domain.model.CalculationInput
import com.thinkx.ada.domain.model.CalculationResult
import java.time.LocalDateTime

/**
 * Pure Kotlin ADA Smart Alarm schedule calculation engine.
 *
 * Implements the mathematical contract:
 * 1. plannedArrivalTime = requiredArrivalTime - safetyBuffer
 * 2. recommendedLeaveTime = plannedArrivalTime - travelDuration
 * 3. recommendedWakeTime = recommendedLeaveTime - preparationDuration
 *
 * Handles date boundaries, overnight departures/wake-ups, and invalid input validation.
 */
object AdaCalculationEngine {

    /**
     * Calculates the complete alarm schedule using a structured [CalculationInput].
     *
     * @param input Validated schedule calculation inputs.
     * @return [CalculationResult] containing the calculated timestamps.
     * @throws IllegalArgumentException if durations are negative or requiredArrival is missing.
     */
    fun calculate(input: CalculationInput): CalculationResult {
        val totalBufferMinutes = input.safetyBufferMinutes + input.weatherBufferMinutes
        val totalCommuteMinutes = input.travelDurationMinutes + input.trafficDelayMinutes

        // 1. plannedArrivalTime = requiredArrivalTime - safetyBuffer - weatherBuffer
        val plannedArrival = input.requiredArrival.minusMinutes(totalBufferMinutes.toLong())

        // 2. recommendedLeaveTime = plannedArrivalTime - travelDuration - trafficDelay
        val recommendedLeaveTime = plannedArrival.minusMinutes(totalCommuteMinutes.toLong())

        // 3. recommendedWakeTime = recommendedLeaveTime - preparationDuration
        val recommendedWakeTime = recommendedLeaveTime.minusMinutes(input.preparationDurationMinutes.toLong())

        return CalculationResult(
            requiredArrival = input.requiredArrival,
            plannedArrival = plannedArrival,
            recommendedLeaveTime = recommendedLeaveTime,
            recommendedWakeTime = recommendedWakeTime,
            travelDurationMinutes = input.travelDurationMinutes,
            preparationDurationMinutes = input.preparationDurationMinutes,
            safetyBufferMinutes = input.safetyBufferMinutes,
            trafficDelayMinutes = input.trafficDelayMinutes,
            weatherBufferMinutes = input.weatherBufferMinutes
        )
    }

    /**
     * Convenience method calculating schedule from scalar values.
     */
    fun calculate(
        requiredArrival: LocalDateTime,
        travelDurationMinutes: Int,
        preparationDurationMinutes: Int,
        safetyBufferMinutes: Int,
        trafficDelayMinutes: Int = 0,
        weatherBufferMinutes: Int = 0
    ): CalculationResult {
        val input = CalculationInput(
            requiredArrival = requiredArrival,
            travelDurationMinutes = travelDurationMinutes,
            preparationDurationMinutes = preparationDurationMinutes,
            safetyBufferMinutes = safetyBufferMinutes,
            trafficDelayMinutes = trafficDelayMinutes,
            weatherBufferMinutes = weatherBufferMinutes
        )
        return calculate(input)
    }

    /**
     * Checks whether an arrival deadline has already elapsed relative to [currentTime].
     */
    fun isDeadlinePast(requiredArrival: LocalDateTime, currentTime: LocalDateTime = LocalDateTime.now()): Boolean {
        return requiredArrival.isBefore(currentTime)
    }

    /**
     * Checks whether the recommended wake-up time has already elapsed relative to [currentTime].
     */
    fun isWakeTimePast(wakeTime: LocalDateTime, currentTime: LocalDateTime = LocalDateTime.now()): Boolean {
        return wakeTime.isBefore(currentTime)
    }
}
