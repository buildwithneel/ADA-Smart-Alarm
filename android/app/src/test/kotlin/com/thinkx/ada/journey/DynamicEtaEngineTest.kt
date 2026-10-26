package com.thinkx.ada.journey

import com.thinkx.ada.domain.journey.engine.DynamicEtaEngine
import com.thinkx.ada.domain.journey.model.DynamicEtaResult
import com.thinkx.ada.domain.journey.model.EtaSource
import com.thinkx.ada.domain.journey.model.JourneyLocationFix
import com.thinkx.ada.domain.journey.model.JourneySchedule
import com.thinkx.ada.domain.journey.routing.RouteResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant
import java.time.ZoneId
import java.time.ZonedDateTime

class DynamicEtaEngineTest {

    // 1. A scheduled journey computes the correct tracking-start time from its lead time.
    @Test
    fun `test 1 - scheduled journey computes correct tracking-start time from lead time`() {
        val departureEpochMs = 1700000000000L
        val leadMinutes = 15
        val expectedStartEpochMs = departureEpochMs - (15 * 60 * 1000L)

        val schedule = JourneySchedule(
            scheduledDepartureEpochMs = departureEpochMs,
            trackingLeadMinutes = leadMinutes
        )

        assertEquals(expectedStartEpochMs, schedule.trackingStartEpochMs)
        assertEquals(expectedStartEpochMs, DynamicEtaEngine.calculateTrackingStartTime(departureEpochMs, leadMinutes))
    }

    // 2. Time zone and date-boundary cases.
    @Test
    fun `test 2 - time zone and date boundary cases cross midnight correctly`() {
        // 00:10 AM in Asia/Kolkata (IST = UTC+5:30) on Oct 27
        val istZone = ZoneId.of("Asia/Kolkata")
        val departureIst = ZonedDateTime.of(2026, 10, 27, 0, 10, 0, 0, istZone)
        val departureEpochMs = departureIst.toInstant().toEpochMilli()

        // 15-minute lead time -> tracking starts at 11:55 PM on Oct 26
        val schedule = JourneySchedule(
            scheduledDepartureEpochMs = departureEpochMs,
            trackingLeadMinutes = 15
        )
        val startInstant = Instant.ofEpochMilli(schedule.trackingStartEpochMs)
        val startIst = ZonedDateTime.ofInstant(startInstant, istZone)

        assertEquals(2026, startIst.year)
        assertEquals(10, startIst.monthValue)
        assertEquals(26, startIst.dayOfMonth)
        assertEquals(23, startIst.hour)
        assertEquals(55, startIst.minute)
    }

    // 3. ETA updates correctly from a valid provider result.
    @Test
    fun `test 3 - ETA updates correctly from a valid provider result`() {
        val now = 1700000000000L
        val fix = JourneyLocationFix(
            latitude = 22.3072,
            longitude = 73.1812,
            accuracyMeters = 8.0f,
            timestampEpochMs = now
        )

        val routeResult = RouteResult(
            distanceMeters = 110_000,
            baseDurationSeconds = 6800,
            trafficDurationSeconds = 7200,
            providerName = "Google Maps",
            isTrafficAware = true
        )

        val etaResult = DynamicEtaEngine.calculateEtaFromProvider(fix, routeResult, currentTimeEpochMs = now)

        assertEquals(now + (7200 * 1000L), etaResult.predictedArrivalEpochMs)
        assertEquals(7200, etaResult.remainingDurationSeconds)
        assertEquals(110_000, etaResult.remainingDistanceMeters)
        assertTrue(etaResult.isTrafficAware)
        assertEquals(EtaSource.TRAFFIC_AWARE_PROVIDER, etaResult.source)
    }

    // 4. Later provider ETA produces a later predicted arrival.
    @Test
    fun `test 4 - later provider duration produces a later predicted arrival`() {
        val now = 1700000000000L
        val fix = JourneyLocationFix(22.3072, 73.1812, 10f, now)

        val baseRoute = RouteResult(100_000, 5000, 5000, providerName = "Google Maps", isTrafficAware = true)
        val worseTrafficRoute = RouteResult(100_000, 5000, 6200, providerName = "Google Maps", isTrafficAware = true)

        val baseEta = DynamicEtaEngine.calculateEtaFromProvider(fix, baseRoute, now)
        val delayedEta = DynamicEtaEngine.calculateEtaFromProvider(fix, worseTrafficRoute, now)

        assertTrue(delayedEta.predictedArrivalEpochMs > baseEta.predictedArrivalEpochMs)
        assertEquals(1200 * 1000L, delayedEta.predictedArrivalEpochMs - baseEta.predictedArrivalEpochMs)
    }

    // 5. Earlier provider ETA produces an earlier predicted arrival.
    @Test
    fun `test 5 - earlier provider duration produces an earlier predicted arrival`() {
        val now = 1700000000000L
        val fix = JourneyLocationFix(22.3072, 73.1812, 10f, now)

        val initialRoute = RouteResult(100_000, 5000, 5000, providerName = "Google Maps", isTrafficAware = true)
        val clearedTrafficRoute = RouteResult(100_000, 5000, 4200, providerName = "Google Maps", isTrafficAware = true)

        val initialEta = DynamicEtaEngine.calculateEtaFromProvider(fix, initialRoute, now)
        val earlierEta = DynamicEtaEngine.calculateEtaFromProvider(fix, clearedTrafficRoute, now)

        assertTrue(earlierEta.predictedArrivalEpochMs < initialEta.predictedArrivalEpochMs)
        assertEquals(800 * 1000L, initialEta.predictedArrivalEpochMs - earlierEta.predictedArrivalEpochMs)
    }

    // 6. Elapsed time is not counted twice.
    @Test
    fun `test 6 - elapsed travel time is not counted twice`() {
        val journeyStartMs = 1700000000000L
        // 30 minutes (1800s) have passed
        val currentFixMs = journeyStartMs + (1800 * 1000L)
        val fix = JourneyLocationFix(22.5000, 73.0000, 10f, currentFixMs)

        // Provider says: remaining duration from this current fix is 3600 seconds
        val routeResult = RouteResult(50_000, 3600, 3600, providerName = "Google Maps", isTrafficAware = true)

        val eta = DynamicEtaEngine.calculateEtaFromProvider(fix, routeResult, currentFixMs)

        // Correct: fix timestamp + remaining duration
        val expectedArrival = currentFixMs + (3600 * 1000L)
        assertEquals(expectedArrival, eta.predictedArrivalEpochMs)

        // Defective double-counting would have added: journeyStartMs + elapsed + remaining + elapsed
        val defectiveDoubleCounted = currentFixMs + (1800 * 1000L) + (3600 * 1000L)
        assertNotEquals(defectiveDoubleCounted, eta.predictedArrivalEpochMs)
    }

    // 7. Stale or invalid location fixes are rejected.
    @Test
    fun `test 7 - stale or invalid location fixes are rejected`() {
        val now = 1700000000000L

        // Fix with poor accuracy (75m > 50m max)
        val poorAccuracyFix = JourneyLocationFix(22.3, 73.1, 75f, now)
        assertFalse(DynamicEtaEngine.isLocationFixValid(poorAccuracyFix, maxAccuracyMeters = 50f, currentTimeMs = now))

        // Stale fix (older than 60s)
        val staleFix = JourneyLocationFix(22.3, 73.1, 10f, now - 90_000L)
        assertFalse(DynamicEtaEngine.isLocationFixValid(staleFix, maxAgeMs = 60_000L, currentTimeMs = now))

        // Clock skew future fix (> 5s in the future)
        val futureFix = JourneyLocationFix(22.3, 73.1, 10f, now + 15_000L)
        assertFalse(DynamicEtaEngine.isLocationFixValid(futureFix, currentTimeMs = now))

        // Valid fix
        val validFix = JourneyLocationFix(22.3, 73.1, 12f, now - 5_000L)
        assertTrue(DynamicEtaEngine.isLocationFixValid(validFix, currentTimeMs = now))
    }

    // 8. GPS jumps do not cause false route deviations.
    @Test
    fun `test 8 - GPS jumps exceeding realistic speed are rejected`() {
        val t0 = 1700000000000L
        val t1 = t0 + 2000L // 2 seconds later

        val fix0 = JourneyLocationFix(22.3000, 73.1000, 10f, t0)
        // 5 km jump in 2 seconds = 2500 m/s (~9000 km/h) with 25m accuracy
        val jumpFix = JourneyLocationFix(22.3450, 73.1000, 25f, t1)

        assertTrue(DynamicEtaEngine.isGpsJump(fix0, jumpFix, maxRealisticSpeedMps = 45f))
    }

    // 9. A genuine route deviation requests recalculation.
    @Test
    fun `test 9 - genuine route deviation triggers recalculation`() {
        // Expected route along longitude 73.1000 between latitude 22.3000 and 22.3500
        val polyline = listOf(
            Pair(22.3000, 73.1000),
            Pair(22.3250, 73.1000),
            Pair(22.3500, 73.1000)
        )

        // Fix on route (within 20m)
        val onRouteFix = JourneyLocationFix(22.3250, 73.1001, 10f, 1700000000000L)
        assertFalse(DynamicEtaEngine.isRouteDeviation(onRouteFix, polyline, deviationThresholdMeters = 250.0))

        // Fix deviated off corridor by ~1.5 km
        val deviatedFix = JourneyLocationFix(22.3250, 73.1150, 10f, 1700000000000L)
        assertTrue(DynamicEtaEngine.isRouteDeviation(deviatedFix, polyline, deviationThresholdMeters = 250.0))

        // When deviated, shouldRecalculateRoute is true immediately
        assertTrue(
            DynamicEtaEngine.shouldRecalculateRoute(
                isDeviated = true,
                lastRequestEpochMs = 1700000000000L - 40_000L,
                lastLocationFix = onRouteFix,
                currentFix = deviatedFix,
                currentTimeEpochMs = 1700000000000L
            )
        )
    }

    // 10. Repeated GPS updates do not repeatedly request an identical route unnecessarily.
    @Test
    fun `test 10 - repeated GPS updates without significant movement or time are throttled`() {
        val t0 = 1700000000000L
        val fix0 = JourneyLocationFix(22.3000, 73.1000, 10f, t0)

        // Moved only 30m after 40 seconds, no deviation
        val fix1 = JourneyLocationFix(22.3002, 73.1001, 10f, t0 + 40_000L)

        val shouldRecalc = DynamicEtaEngine.shouldRecalculateRoute(
            isDeviated = false,
            lastRequestEpochMs = t0,
            lastLocationFix = fix0,
            currentFix = fix1,
            currentTimeEpochMs = t0 + 40_000L,
            minDistanceDeltaMeters = 200.0,
            minIntervalSec = 180L
        )

        assertFalse("Repeated update should be throttled", shouldRecalc)
    }

    // 11. Traffic-aware ETA is not double-counted with a stop penalty.
    @Test
    fun `test 11 - traffic-aware ETA does not double count stop penalties`() {
        val now = 1700000000000L
        val fix = JourneyLocationFix(22.3000, 73.1000, 10f, now)

        val trafficRoute = RouteResult(
            distanceMeters = 60_000,
            baseDurationSeconds = 3000,
            trafficDurationSeconds = 3800, // already contains +800s congestion delay
            providerName = "Google Maps",
            isTrafficAware = true
        )

        val eta = DynamicEtaEngine.calculateEtaFromProvider(fix, trafficRoute, now)

        // Duration used must be exactly 3800s, not 3800 + 800 or 3800 + fixed buffer
        assertEquals(3800, eta.remainingDurationSeconds)
        assertEquals(now + (3800 * 1000L), eta.predictedArrivalEpochMs)
    }

    // 12. Fallback estimates are labeled as non-traffic-aware.
    @Test
    fun `test 12 - fallback estimates are explicitly labeled as non-traffic-aware`() {
        val now = 1700000000000L
        val fix = JourneyLocationFix(22.3000, 73.1000, 10f, now)

        val fallbackEta = DynamicEtaEngine.calculateFallbackEta(
            fix = fix,
            destinationLat = 22.5000,
            destinationLng = 73.1000,
            averageSpeedMps = 11.11,
            currentTimeEpochMs = now
        )

        assertFalse(fallbackEta.isTrafficAware)
        assertEquals(EtaSource.NON_TRAFFIC_FALLBACK, fallbackEta.source)
        assertTrue(fallbackEta.remainingDistanceMeters > 0)
        assertTrue(fallbackEta.remainingDurationSeconds > 0)
    }

    // 13. Provider failures preserve the last valid ETA while marking its freshness correctly.
    @Test
    fun `test 13 - stale ETA is marked appropriately when refresh window passes`() {
        val t0 = 1700000000000L
        val freshEta = DynamicEtaResult(
            predictedArrivalEpochMs = t0 + (3600 * 1000L),
            remainingDurationSeconds = 3600,
            remainingDistanceMeters = 40_000,
            isTrafficAware = true,
            source = EtaSource.TRAFFIC_AWARE_PROVIDER,
            providerName = "Google Maps",
            lastRefreshEpochMs = t0
        )

        // 2 minutes later: still fresh
        val checked2m = freshEta.checkStaleness(t0 + 120_000L, stalenessThresholdMs = 300_000L)
        assertFalse(checked2m.isStale)

        // 6 minutes later: stale
        val checked6m = freshEta.checkStaleness(t0 + 360_000L, stalenessThresholdMs = 300_000L)
        assertTrue(checked6m.isStale)
        assertEquals(freshEta.predictedArrivalEpochMs, checked6m.predictedArrivalEpochMs) // Preserves last valid ETA!
    }

    // 14. Approach threshold crossing triggers once.
    @Test
    fun `test 14 - approach threshold crossing triggers once idempotently`() {
        // Far away (1500m > 1000m)
        assertFalse(DynamicEtaEngine.checkApproachingAlert(1500, approachingThresholdMeters = 1000, alreadyAlerted = false))

        // Crosses threshold (900m <= 1000m)
        assertTrue(DynamicEtaEngine.checkApproachingAlert(900, approachingThresholdMeters = 1000, alreadyAlerted = false))

        // Subsequent updates in threshold when already alerted must NOT re-trigger
        assertFalse(DynamicEtaEngine.checkApproachingAlert(850, approachingThresholdMeters = 1000, alreadyAlerted = true))
        assertFalse(DynamicEtaEngine.checkApproachingAlert(400, approachingThresholdMeters = 1000, alreadyAlerted = true))
    }

    // 15. Arrival requires reliable confirmation.
    @Test
    fun `test 15 - arrival requires accurate fix and consecutive confirmation`() {
        // Inaccurate fix (accuracy 65m > 50m) within 80m must NOT confirm arrival
        assertFalse(
            DynamicEtaEngine.checkArrivalConfirmation(
                currentDistanceMeters = 80,
                accuracyMeters = 65f,
                arrivalThresholdMeters = 100,
                consecutiveConfirmations = 2,
                requiredConfirmations = 2
            )
        )

        // Accurate fix, but only 1 confirmation hit when 2 required
        assertFalse(
            DynamicEtaEngine.checkArrivalConfirmation(
                currentDistanceMeters = 80,
                accuracyMeters = 15f,
                arrivalThresholdMeters = 100,
                consecutiveConfirmations = 1,
                requiredConfirmations = 2
            )
        )

        // Accurate fix with confirmed 2 consecutive hits -> ARRIVAL CONFIRMED!
        assertTrue(
            DynamicEtaEngine.checkArrivalConfirmation(
                currentDistanceMeters = 80,
                accuracyMeters = 15f,
                arrivalThresholdMeters = 100,
                consecutiveConfirmations = 2,
                requiredConfirmations = 2
            )
        )
    }
}
