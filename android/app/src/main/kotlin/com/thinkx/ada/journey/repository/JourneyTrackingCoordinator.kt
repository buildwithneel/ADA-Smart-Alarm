package com.thinkx.ada.journey.repository

import android.util.Log
import com.thinkx.ada.data.local.dao.AlarmDao
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.domain.journey.engine.DynamicEtaEngine
import com.thinkx.ada.domain.journey.model.DynamicEtaResult
import com.thinkx.ada.domain.journey.model.JourneyAlertEvent
import com.thinkx.ada.domain.journey.model.JourneyLocationFix
import com.thinkx.ada.domain.journey.model.JourneyState
import com.thinkx.ada.domain.journey.routing.RouteRequest
import com.thinkx.ada.domain.journey.routing.RoutingProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt

data class TrackingUpdateResult(
    val journeyState: JourneyState,
    val etaResult: DynamicEtaResult?,
    val remainingDistanceMeters: Int,
    val alertEvent: JourneyAlertEvent? = null,
    val isDeviation: Boolean = false
)

class JourneyTrackingCoordinator(
    private val alarmDao: AlarmDao,
    private val routingProvider: RoutingProvider,
    private val nowProvider: () -> Long = { System.currentTimeMillis() }
) {

    companion object {
        private const val TAG = "AdaJourneyCoordinator"
    }

    private var previousFix: JourneyLocationFix? = null
    private var lastRequestEpochMs: Long = 0L
    private var cachedPolylinePoints: List<Pair<Double, Double>> = emptyList()
    private var consecutiveArrivalHits: Int = 0

    suspend fun processLocationFix(
        journeyId: String,
        currentFix: JourneyLocationFix
    ): TrackingUpdateResult = withContext(Dispatchers.IO) {
        val journey = alarmDao.getAlarmById(journeyId)
            ?: return@withContext TrackingUpdateResult(
                journeyState = JourneyState.FAILED,
                etaResult = null,
                remainingDistanceMeters = 0
            )

        // 1. Validate fix accuracy and freshness
        val now = nowProvider()
        if (!DynamicEtaEngine.isLocationFixValid(currentFix, currentTimeMs = now)) {
            Log.w(TAG, "Discarded inaccurate or stale GPS fix: accuracy=${currentFix.accuracyMeters}m, age=${now - currentFix.timestampEpochMs}ms")
            return@withContext TrackingUpdateResult(
                journeyState = JourneyState.TRACKING_DEGRADED,
                etaResult = null,
                remainingDistanceMeters = journey.remainingDistanceMeters ?: 0
            )
        }

        // 2. Protect against unrealistic GPS position jumps
        val lastFix = previousFix
        if (lastFix != null && DynamicEtaEngine.isGpsJump(lastFix, currentFix)) {
            Log.w(TAG, "Rejected GPS jump fix from $lastFix to $currentFix")
            return@withContext TrackingUpdateResult(
                journeyState = JourneyState.ACTIVE_TRACKING,
                etaResult = null,
                remainingDistanceMeters = journey.remainingDistanceMeters ?: 0
            )
        }
        previousFix = currentFix

        // 3. Check for route deviation
        val isDeviated = if (cachedPolylinePoints.isNotEmpty()) {
            DynamicEtaEngine.isRouteDeviation(currentFix, cachedPolylinePoints)
        } else {
            false
        }

        // 4. Determine if we should query routing provider
        val shouldRecalculate = DynamicEtaEngine.shouldRecalculateRoute(
            isDeviated = isDeviated,
            lastRequestEpochMs = lastRequestEpochMs,
            lastLocationFix = lastFix,
            currentFix = currentFix,
            currentTimeEpochMs = now
        )

        var etaResult: DynamicEtaResult? = null

        if (shouldRecalculate || journey.currentEtaEpochMs == null) {
            lastRequestEpochMs = now
            val routeRequest = RouteRequest(
                originLat = currentFix.latitude,
                originLng = currentFix.longitude,
                destinationLat = journey.destinationLat,
                destinationLng = journey.destinationLng
            )

            val providerResult = routingProvider.calculateRoute(routeRequest)
            if (providerResult.isSuccess) {
                val route = providerResult.getOrThrow()
                etaResult = DynamicEtaEngine.calculateEtaFromProvider(currentFix, route, now)
                if (route.routeGeometry.isNotBlank()) {
                    cachedPolylinePoints = DynamicEtaEngine.decodePolyline(route.routeGeometry)
                }
            } else {
                Log.w(TAG, "Routing provider calculation failed; using fallback: ${providerResult.exceptionOrNull()?.message}")
                etaResult = DynamicEtaEngine.calculateFallbackEta(
                    fix = currentFix,
                    destinationLat = journey.destinationLat,
                    destinationLng = journey.destinationLng,
                    currentTimeEpochMs = now
                )
            }
        } else {
            // Re-compute remaining distance to destination along with time elapsed
            val remainingDistance = currentFix.distanceTo(journey.destinationLat, journey.destinationLng).roundToInt()
            val existingEta = journey.currentEtaEpochMs
            val remainingSec = ((existingEta - now) / 1000L).coerceAtLeast(0).toInt()
            etaResult = DynamicEtaResult(
                predictedArrivalEpochMs = existingEta,
                remainingDurationSeconds = remainingSec,
                remainingDistanceMeters = remainingDistance,
                isTrafficAware = journey.isTrafficAware,
                source = if (journey.isTrafficAware) com.thinkx.ada.domain.journey.model.EtaSource.TRAFFIC_AWARE_PROVIDER else com.thinkx.ada.domain.journey.model.EtaSource.NON_TRAFFIC_FALLBACK,
                providerName = journey.etaSource,
                lastRefreshEpochMs = journey.lastCalculatedEpochMs,
                isStale = (now - journey.lastCalculatedEpochMs) > 300_000L
            )
        }

        val remainingDist = etaResult.remainingDistanceMeters

        // 5. Evaluate Arrival Confirmation (100m default threshold)
        if (remainingDist <= journey.arrivalThresholdMeters && currentFix.accuracyMeters <= 50f) {
            consecutiveArrivalHits++
        } else {
            consecutiveArrivalHits = 0
        }

        val isArrived = DynamicEtaEngine.checkArrivalConfirmation(
            currentDistanceMeters = remainingDist,
            accuracyMeters = currentFix.accuracyMeters,
            arrivalThresholdMeters = journey.arrivalThresholdMeters,
            consecutiveConfirmations = consecutiveArrivalHits,
            requiredConfirmations = 2
        )

        var alertEvent: JourneyAlertEvent? = null
        var nextStatus = AlarmEntity.STATUS_ACTIVE_TRACKING
        var approachingSent = journey.isApproachingAlertSent
        var arrivalConfirmed = journey.isArrivalConfirmed

        if (isArrived && !arrivalConfirmed) {
            arrivalConfirmed = true
            nextStatus = AlarmEntity.STATUS_ARRIVED
            alertEvent = JourneyAlertEvent.ARRIVAL_CONFIRMED
            Log.i(TAG, "Confirmed arrival at destination for journey $journeyId")
        } else if (DynamicEtaEngine.checkApproachingAlert(remainingDist, journey.approachingThresholdMeters, approachingSent)) {
            approachingSent = true
            nextStatus = AlarmEntity.STATUS_APPROACHING
            alertEvent = JourneyAlertEvent.APPROACHING_ALERT
            Log.i(TAG, "Approaching destination alert triggered for journey $journeyId (distance: ${remainingDist}m)")
        } else if (isDeviated) {
            nextStatus = AlarmEntity.STATUS_RECALCULATING
        }

        // 6. Persist state in Room database
        val updatedJourney = journey.copy(
            status = nextStatus,
            currentEtaEpochMs = etaResult.predictedArrivalEpochMs,
            remainingDistanceMeters = remainingDist,
            remainingDurationSeconds = etaResult.remainingDurationSeconds,
            lastLocationLat = currentFix.latitude,
            lastLocationLng = currentFix.longitude,
            lastLocationEpochMs = currentFix.timestampEpochMs,
            isTrafficAware = etaResult.isTrafficAware,
            etaSource = etaResult.providerName,
            isApproachingAlertSent = approachingSent,
            isArrivalConfirmed = arrivalConfirmed,
            arrivalConfirmedEpochMs = if (arrivalConfirmed && journey.arrivalConfirmedEpochMs == null) now else journey.arrivalConfirmedEpochMs,
            lastCalculatedEpochMs = now,
            updatedAtEpochMs = now
        )

        alarmDao.updateAlarm(updatedJourney)

        val stateEnum = when (nextStatus) {
            AlarmEntity.STATUS_ARRIVED -> JourneyState.ARRIVED
            AlarmEntity.STATUS_APPROACHING -> JourneyState.APPROACHING
            AlarmEntity.STATUS_RECALCULATING -> JourneyState.RECALCULATING
            else -> JourneyState.ACTIVE_TRACKING
        }

        return@withContext TrackingUpdateResult(
            journeyState = stateEnum,
            etaResult = etaResult,
            remainingDistanceMeters = remainingDist,
            alertEvent = alertEvent,
            isDeviation = isDeviated
        )
    }
}
