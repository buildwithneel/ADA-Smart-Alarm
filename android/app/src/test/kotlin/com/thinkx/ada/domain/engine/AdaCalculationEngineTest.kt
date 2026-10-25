package com.thinkx.ada.domain.engine

import com.thinkx.ada.domain.model.CalculationInput
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime

class AdaCalculationEngineTest {

    @Test
    fun `canonical example from specification - Charusat arrival 9am`() {
        // User sets:
        // - Required arrival: 9:00 AM
        // - Estimated travel duration: 35 minutes
        // - Preparation duration: 30 minutes
        // - Safety buffer: 10 minutes
        //
        // ADA calculates:
        // - Planned arrival: 8:50 AM
        // - Recommended departure: 8:15 AM
        // - Recommended wake-up: 7:45 AM
        val targetDate = LocalDate.of(2026, 10, 26)
        val requiredArrival = LocalDateTime.of(targetDate, LocalTime.of(9, 0))

        val result = AdaCalculationEngine.calculate(
            requiredArrival = requiredArrival,
            travelDurationMinutes = 35,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10
        )

        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(8, 50)), result.plannedArrival)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(8, 15)), result.recommendedLeaveTime)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(7, 45)), result.recommendedWakeTime)

        assertEquals("8:50 AM", result.formattedPlannedArrival)
        assertEquals("8:15 AM", result.formattedRecommendedLeaveTime)
        assertEquals("7:45 AM", result.formattedRecommendedWakeTime)

        assertFalse(result.isOvernightWakeUp)
        assertFalse(result.isOvernightDeparture)
    }

    @Test
    fun `zero safety buffer aligns planned arrival with required arrival`() {
        val targetDate = LocalDate.of(2026, 10, 26)
        val requiredArrival = LocalDateTime.of(targetDate, LocalTime.of(10, 0))

        val result = AdaCalculationEngine.calculate(
            requiredArrival = requiredArrival,
            travelDurationMinutes = 20,
            preparationDurationMinutes = 15,
            safetyBufferMinutes = 0
        )

        assertEquals(requiredArrival, result.plannedArrival)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(9, 40)), result.recommendedLeaveTime)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(9, 25)), result.recommendedWakeTime)
    }

    @Test
    fun `zero preparation duration aligns wake-up with departure`() {
        val targetDate = LocalDate.of(2026, 10, 26)
        val requiredArrival = LocalDateTime.of(targetDate, LocalTime.of(8, 30))

        val result = AdaCalculationEngine.calculate(
            requiredArrival = requiredArrival,
            travelDurationMinutes = 30,
            preparationDurationMinutes = 0,
            safetyBufferMinutes = 10
        )

        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(8, 20)), result.plannedArrival)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(7, 50)), result.recommendedLeaveTime)
        assertEquals(result.recommendedLeaveTime, result.recommendedWakeTime)
    }

    @Test
    fun `overnight schedule crossing midnight correctly shifts departure and wake-up to previous day`() {
        // Arrival deadline: 1:00 AM on Day 2
        // Travel: 45 min
        // Prep: 60 min
        // Safety: 30 min
        // Total before arrival: 135 min (2h 15m)
        // Planned arrival: 12:30 AM on Day 2
        // Recommended departure: 11:45 PM on Day 1
        // Recommended wake-up: 10:45 PM on Day 1
        val day1 = LocalDate.of(2026, 10, 25)
        val day2 = LocalDate.of(2026, 10, 26)
        val requiredArrival = LocalDateTime.of(day2, LocalTime.of(1, 0))

        val result = AdaCalculationEngine.calculate(
            requiredArrival = requiredArrival,
            travelDurationMinutes = 45,
            preparationDurationMinutes = 60,
            safetyBufferMinutes = 30
        )

        assertEquals(LocalDateTime.of(day2, LocalTime.of(0, 30)), result.plannedArrival)
        assertEquals(LocalDateTime.of(day1, LocalTime.of(23, 45)), result.recommendedLeaveTime)
        assertEquals(LocalDateTime.of(day1, LocalTime.of(22, 45)), result.recommendedWakeTime)

        assertTrue(result.isOvernightDeparture)
        assertTrue(result.isOvernightWakeUp)
    }

    @Test
    fun `traffic delay shifts departure and wake times earlier without changing planned arrival`() {
        val targetDate = LocalDate.of(2026, 10, 26)
        val requiredArrival = LocalDateTime.of(targetDate, LocalTime.of(9, 0))

        val baseline = AdaCalculationEngine.calculate(
            requiredArrival = requiredArrival,
            travelDurationMinutes = 30,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            trafficDelayMinutes = 0
        )

        val withTraffic = AdaCalculationEngine.calculate(
            requiredArrival = requiredArrival,
            travelDurationMinutes = 30,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            trafficDelayMinutes = 20
        )

        // Planned arrival stays unaffected
        assertEquals(baseline.plannedArrival, withTraffic.plannedArrival)

        // Departure and wake-up are shifted earlier by traffic delay (20 min)
        assertEquals(baseline.recommendedLeaveTime.minusMinutes(20), withTraffic.recommendedLeaveTime)
        assertEquals(baseline.recommendedWakeTime.minusMinutes(20), withTraffic.recommendedWakeTime)
    }

    @Test
    fun `weather buffer expands total safety cushion`() {
        val targetDate = LocalDate.of(2026, 10, 26)
        val requiredArrival = LocalDateTime.of(targetDate, LocalTime.of(9, 0))

        val result = AdaCalculationEngine.calculate(
            requiredArrival = requiredArrival,
            travelDurationMinutes = 30,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            weatherBufferMinutes = 15
        )

        assertEquals(25, result.totalBufferMinutes)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(8, 35)), result.plannedArrival)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(8, 5)), result.recommendedLeaveTime)
        assertEquals(LocalDateTime.of(targetDate, LocalTime.of(7, 35)), result.recommendedWakeTime)
    }

    @Test
    fun `negative inputs are rejected with descriptive exceptions`() {
        val deadline = LocalDateTime.of(2026, 10, 26, 9, 0)

        assertThrows(IllegalArgumentException::class.java) {
            CalculationInput(deadline, travelDurationMinutes = -1, preparationDurationMinutes = 30, safetyBufferMinutes = 10)
        }
        assertThrows(IllegalArgumentException::class.java) {
            CalculationInput(deadline, travelDurationMinutes = 30, preparationDurationMinutes = -5, safetyBufferMinutes = 10)
        }
        assertThrows(IllegalArgumentException::class.java) {
            CalculationInput(deadline, travelDurationMinutes = 30, preparationDurationMinutes = 30, safetyBufferMinutes = -10)
        }
        assertThrows(IllegalArgumentException::class.java) {
            CalculationInput(deadline, travelDurationMinutes = 30, preparationDurationMinutes = 30, safetyBufferMinutes = 10, trafficDelayMinutes = -2)
        }
        assertThrows(IllegalArgumentException::class.java) {
            CalculationInput(deadline, travelDurationMinutes = 30, preparationDurationMinutes = 30, safetyBufferMinutes = 10, weatherBufferMinutes = -3)
        }
    }

    @Test
    fun `deadline and wake time past checks`() {
        val referenceNow = LocalDateTime.of(2026, 10, 26, 8, 0)
        val pastDeadline = LocalDateTime.of(2026, 10, 26, 7, 59)
        val futureDeadline = LocalDateTime.of(2026, 10, 26, 8, 1)

        assertTrue(AdaCalculationEngine.isDeadlinePast(pastDeadline, referenceNow))
        assertFalse(AdaCalculationEngine.isDeadlinePast(futureDeadline, referenceNow))

        val pastWake = LocalDateTime.of(2026, 10, 26, 7, 30)
        val futureWake = LocalDateTime.of(2026, 10, 26, 8, 15)

        assertTrue(AdaCalculationEngine.isWakeTimePast(pastWake, referenceNow))
        assertFalse(AdaCalculationEngine.isWakeTimePast(futureWake, referenceNow))
    }
}
