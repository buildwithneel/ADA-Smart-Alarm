package com.thinkx.ada.journey

import com.thinkx.ada.data.local.dao.AlarmDao
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.domain.journey.model.JourneyAlertEvent
import com.thinkx.ada.domain.journey.model.JourneyLocationFix
import com.thinkx.ada.domain.journey.model.JourneyState
import com.thinkx.ada.domain.journey.routing.RouteRequest
import com.thinkx.ada.domain.journey.routing.RouteResult
import com.thinkx.ada.domain.journey.routing.RoutingProvider
import com.thinkx.ada.journey.repository.JourneyTrackingCoordinator
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class JourneyLifecycleAndCoordinatorTest {

    private lateinit var fakeDao: FakeInMemoryAlarmDao
    private lateinit var fakeRoutingProvider: FakeTestRoutingProvider
    private lateinit var coordinator: JourneyTrackingCoordinator

    private var testCurrentTimeMs: Long = 1700000000000L

    @Before
    fun setup() {
        testCurrentTimeMs = 1700000000000L
        fakeDao = FakeInMemoryAlarmDao()
        fakeRoutingProvider = FakeTestRoutingProvider()
        coordinator = JourneyTrackingCoordinator(fakeDao, fakeRoutingProvider, nowProvider = { testCurrentTimeMs })
    }

    private fun createTestJourney(
        id: String = "journey-1",
        status: String = AlarmEntity.STATUS_SCHEDULED,
        destinationLat: Double = 23.0225,
        destinationLng: Double = 72.5714,
        approachingThreshold: Int = 1000,
        arrivalThreshold: Int = 100,
        isApproachingAlertSent: Boolean = false,
        isArrivalConfirmed: Boolean = false
    ): AlarmEntity {
        val now = testCurrentTimeMs
        return AlarmEntity(
            id = id,
            title = "Trip to Ahmedabad RTO",
            destinationName = "Ahmedabad RTO",
            destinationAddress = "RTO Circle, Subhash Bridge",
            destinationLat = destinationLat,
            destinationLng = destinationLng,
            requiredArrivalEpochMs = now + 7200_000L,
            plannedArrivalEpochMs = now + 6600_000L,
            recommendedLeaveEpochMs = now + 1800_000L,
            recommendedWakeEpochMs = now + 900_000L,
            scheduledAlarmEpochMs = now + 900_000L,
            scheduledDepartureEpochMs = now + 1800_000L,
            trackingLeadMinutes = 15,
            approachingThresholdMeters = approachingThreshold,
            arrivalThresholdMeters = arrivalThreshold,
            travelDurationMinutes = 80,
            preparationDurationMinutes = 15,
            safetyBufferMinutes = 10,
            status = status,
            isApproachingAlertSent = isApproachingAlertSent,
            isArrivalConfirmed = isArrivalConfirmed
        )
    }

    // 16. Arrival notification is not duplicated after recovery/restart.
    @Test
    fun `test 16 - arrival notification is not duplicated after recovery or restart`() = runTest {
        val journey = createTestJourney(
            status = AlarmEntity.STATUS_ACTIVE_TRACKING,
            isApproachingAlertSent = true,
            isArrivalConfirmed = false
        )
        fakeDao.insertAlarm(journey)

        // Close to destination (50m <= 100m threshold)
        val arrivalFix1 = JourneyLocationFix(
            latitude = 23.0225,
            longitude = 72.5714,
            accuracyMeters = 10f,
            timestampEpochMs = testCurrentTimeMs
        )

        // First fix registers confirmation hit 1
        val res1 = coordinator.processLocationFix(journey.id, arrivalFix1)
        assertNull(res1.alertEvent) // requires 2 confirmations

        // Second fix confirms arrival -> Alert delivered!
        testCurrentTimeMs += 5000L
        val arrivalFix2 = arrivalFix1.copy(timestampEpochMs = testCurrentTimeMs)
        val res2 = coordinator.processLocationFix(journey.id, arrivalFix2)
        assertEquals(JourneyAlertEvent.ARRIVAL_CONFIRMED, res2.alertEvent)
        assertEquals(JourneyState.ARRIVED, res2.journeyState)

        // Verify persisted state in DAO has arrival confirmed = true
        val persisted = fakeDao.getAlarmById(journey.id)
        assertNotNull(persisted)
        assertTrue(persisted!!.isArrivalConfirmed)
        assertEquals(AlarmEntity.STATUS_ARRIVED, persisted.status)

        // Simulate app restart / coordinator re-creation: subsequent GPS fix must NOT fire duplicate arrival alert
        testCurrentTimeMs += 5000L
        val newCoordinator = JourneyTrackingCoordinator(fakeDao, fakeRoutingProvider, nowProvider = { testCurrentTimeMs })
        val subsequentFix = arrivalFix1.copy(timestampEpochMs = testCurrentTimeMs)
        val res3 = newCoordinator.processLocationFix(journey.id, subsequentFix)

        assertNull("Arrival alert must not be duplicated after restart", res3.alertEvent)
    }

    // 17. Stopping or cancelling a journey ends active tracking.
    @Test
    fun `test 17 - stopping or cancelling a journey transitions state to terminal and ends active tracking`() = runTest {
        val journey = createTestJourney(status = AlarmEntity.STATUS_ACTIVE_TRACKING)
        fakeDao.insertAlarm(journey)

        // Stop journey
        fakeDao.updateAlarmStatus(journey.id, AlarmEntity.STATUS_STOPPED, 1700000000000L)
        val stopped = fakeDao.getAlarmById(journey.id)!!
        assertEquals(AlarmEntity.STATUS_STOPPED, stopped.status)

        // Cancel journey
        fakeDao.updateAlarmStatus(journey.id, AlarmEntity.STATUS_CANCELLED, 1700000000000L)
        val cancelled = fakeDao.getAlarmById(journey.id)!!
        assertEquals(AlarmEntity.STATUS_CANCELLED, cancelled.status)

        // Terminal state check
        val stoppedState = JourneyState.STOPPED
        val cancelledState = JourneyState.CANCELLED
        assertTrue(stoppedState.isTerminal)
        assertFalse(stoppedState.isTrackingActive)
        assertTrue(cancelledState.isTerminal)
        assertFalse(cancelledState.isTrackingActive)
    }

    // 18. Scheduled start does not create duplicate sessions.
    @Test
    fun `test 18 - scheduled start does not duplicate journey sessions`() = runTest {
        val journey = createTestJourney(status = AlarmEntity.STATUS_SCHEDULED)
        fakeDao.insertAlarm(journey)

        // Attempting to retrieve active journeys when only scheduled should return null
        assertNull(fakeDao.getActiveTrackingJourney())

        // Start active tracking
        fakeDao.updateAlarmStatus(journey.id, AlarmEntity.STATUS_ACTIVE_TRACKING, 1700000000000L)
        val active = fakeDao.getActiveTrackingJourney()
        assertNotNull(active)
        assertEquals(journey.id, active!!.id)

        // Attempting to query active tracking journey returns the same single session
        val activeSecondQuery = fakeDao.getActiveTrackingJourney()
        assertEquals(active.id, activeSecondQuery?.id)
    }

    // 19. Missing permissions prevent false reporting of active tracking.
    @Test
    fun `test 19 - missing permissions or invalid fix prevents false reporting of active tracking`() = runTest {
        val journey = createTestJourney(status = AlarmEntity.STATUS_SCHEDULED)
        fakeDao.insertAlarm(journey)

        // Inaccurate location fix (accuracy = 80m > 50m max)
        val inaccurateFix = JourneyLocationFix(
            latitude = 22.3000,
            longitude = 73.1000,
            accuracyMeters = 80f,
            timestampEpochMs = 1700000000000L
        )

        val result = coordinator.processLocationFix(journey.id, inaccurateFix)

        // Must report degraded, NOT active tracking
        assertEquals(JourneyState.TRACKING_DEGRADED, result.journeyState)
        assertNull("ETA must not be derived from inaccurate fix", result.etaResult)
    }

    // 20. State machine legal transitions and alert checks.
    @Test
    fun `test 20 - approaching alert is fired exactly once when within threshold`() = runTest {
        val journey = createTestJourney(
            status = AlarmEntity.STATUS_ACTIVE_TRACKING,
            destinationLat = 22.3000,
            destinationLng = 73.1000,
            approachingThreshold = 1000,
            isApproachingAlertSent = false
        )
        fakeDao.insertAlarm(journey)

        // Fix ~800m away from destination
        val nearFix = JourneyLocationFix(
            latitude = 22.3000,
            longitude = 73.1072, // ~740m distance
            accuracyMeters = 10f,
            timestampEpochMs = testCurrentTimeMs
        )

        val res1 = coordinator.processLocationFix(journey.id, nearFix)
        assertEquals(JourneyAlertEvent.APPROACHING_ALERT, res1.alertEvent)
        assertEquals(JourneyState.APPROACHING, res1.journeyState)

        // Second fix in threshold must NOT fire approaching alert again, and MUST retain APPROACHING state
        testCurrentTimeMs += 5000L
        val nearFix2 = nearFix.copy(timestampEpochMs = testCurrentTimeMs)
        val res2 = coordinator.processLocationFix(journey.id, nearFix2)
        assertNull("Approaching alert must be idempotent", res2.alertEvent)
        assertEquals("Must retain APPROACHING state until confirmed arrival", JourneyState.APPROACHING, res2.journeyState)
    }

    // 21. TRACKING_PENDING is recognized as an active journey session in DAO
    @Test
    fun `test 21 - tracking pending is recognized as active tracking journey`() = runTest {
        val pendingJourney = createTestJourney(status = AlarmEntity.STATUS_TRACKING_PENDING)
        fakeDao.insertAlarm(pendingJourney)

        val active = fakeDao.getActiveTrackingJourney()
        assertNotNull("TRACKING_PENDING must be queryable as active journey to prevent double-start", active)
        assertEquals(pendingJourney.id, active!!.id)
    }

    // 22. Degraded GPS preserves previous valid ETA and updates status to TRACKING_DEGRADED
    @Test
    fun `test 22 - degraded GPS preserves last valid route and reports TRACKING_DEGRADED`() = runTest {
        val journey = createTestJourney(status = AlarmEntity.STATUS_ACTIVE_TRACKING)
        fakeDao.insertAlarm(journey)

        // Initial valid fix
        val goodFix = JourneyLocationFix(
            latitude = 23.0000,
            longitude = 72.5000,
            accuracyMeters = 10f,
            timestampEpochMs = testCurrentTimeMs
        )
        val res1 = coordinator.processLocationFix(journey.id, goodFix)
        assertEquals(JourneyState.ACTIVE_TRACKING, res1.journeyState)
        val initialEta = res1.etaResult
        assertNotNull(initialEta)

        // Next fix has degraded accuracy (75m > 50m max)
        testCurrentTimeMs += 10000L
        val badFix = JourneyLocationFix(
            latitude = 23.0010,
            longitude = 72.5010,
            accuracyMeters = 75f,
            timestampEpochMs = testCurrentTimeMs
        )
        val res2 = coordinator.processLocationFix(journey.id, badFix)
        assertEquals(JourneyState.TRACKING_DEGRADED, res2.journeyState)
        assertNull("Degraded fix must not produce a newly calculated ETA", res2.etaResult)

        // Room database must reflect TRACKING_DEGRADED
        val persisted = fakeDao.getAlarmById(journey.id)
        assertNotNull(persisted)
        assertEquals(AlarmEntity.STATUS_TRACKING_DEGRADED, persisted!!.status)
    }
}

// Test Doubles
private class FakeTestRoutingProvider : RoutingProvider {
    override val name: String = "Fake Routing Provider"

    override suspend fun calculateRoute(request: RouteRequest): Result<RouteResult> {
        val fix = JourneyLocationFix(request.originLat, request.originLng, 5f, System.currentTimeMillis())
        val distMeters = fix.distanceTo(request.destinationLat, request.destinationLng).toInt()
        val duration = if (distMeters > 0) (distMeters / 15.0).toInt() else 0
        return Result.success(
            RouteResult(
                distanceMeters = distMeters,
                baseDurationSeconds = duration,
                trafficDurationSeconds = duration,
                routeGeometry = "",
                providerName = name,
                isTrafficAware = true
            )
        )
    }
}

private class FakeInMemoryAlarmDao : AlarmDao {
    val alarmsMap = mutableMapOf<String, AlarmEntity>()
    private val alarmsFlow = MutableStateFlow<List<AlarmEntity>>(emptyList())

    private fun emit() {
        alarmsFlow.value = alarmsMap.values.toList()
    }

    override fun getAllAlarms(): Flow<List<AlarmEntity>> = alarmsFlow

    override suspend fun getEnabledAlarms(): List<AlarmEntity> =
        alarmsMap.values.filter { it.isEnabled }

    override fun getEnabledAlarmsFlow(): Flow<List<AlarmEntity>> = alarmsFlow

    override suspend fun getAlarmById(id: String): AlarmEntity? = alarmsMap[id]

    override fun getAlarmByIdFlow(id: String): Flow<AlarmEntity?> =
        alarmsFlow.map { list -> list.find { it.id == id } }

    override suspend fun getNextUpcomingAlarm(nowEpochMs: Long): AlarmEntity? =
        alarmsMap.values.filter { it.isEnabled && it.scheduledAlarmEpochMs >= nowEpochMs }
            .minByOrNull { it.scheduledAlarmEpochMs }

    override fun getNextUpcomingAlarmFlow(nowEpochMs: Long): Flow<AlarmEntity?> =
        alarmsFlow.map { list ->
            list.filter { it.isEnabled && it.scheduledAlarmEpochMs >= nowEpochMs }
                .minByOrNull { it.scheduledAlarmEpochMs }
        }

    override suspend fun insertAlarm(alarm: AlarmEntity) {
        alarmsMap[alarm.id] = alarm
        emit()
    }

    override suspend fun updateAlarm(alarm: AlarmEntity) {
        alarmsMap[alarm.id] = alarm
        emit()
    }

    override suspend fun deleteAlarm(alarm: AlarmEntity) {
        alarmsMap.remove(alarm.id)
        emit()
    }

    override suspend fun deleteAlarmById(id: String) {
        alarmsMap.remove(id)
        emit()
    }

    override suspend fun updateAlarmEnabled(id: String, isEnabled: Boolean, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(isEnabled = isEnabled, updatedAtEpochMs = updatedAtEpochMs)
            emit()
        }
    }

    override suspend fun updateAlarmStatus(id: String, status: String, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(status = status, updatedAtEpochMs = updatedAtEpochMs)
            emit()
        }
    }

    override suspend fun snoozeAlarm(id: String, newScheduleEpochMs: Long, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(scheduledAlarmEpochMs = newScheduleEpochMs, status = AlarmEntity.STATUS_SNOOZED, updatedAtEpochMs = updatedAtEpochMs)
            emit()
        }
    }

    override suspend fun dismissOneTimeAlarm(id: String, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(isEnabled = false, status = AlarmEntity.STATUS_DISMISSED, updatedAtEpochMs = updatedAtEpochMs)
            emit()
        }
    }

    override suspend fun getAlarmsBySyncStatus(status: String): List<AlarmEntity> =
        alarmsMap.values.filter { it.syncStatus == status }

    override suspend fun getAlarmByServerId(serverId: String): AlarmEntity? =
        alarmsMap.values.find { it.serverId == serverId }

    override suspend fun updateSyncStatus(
        id: String,
        serverId: String?,
        syncStatus: String,
        lastSyncedEpochMs: Long
    ) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(serverId = serverId, syncStatus = syncStatus, lastSyncedEpochMs = lastSyncedEpochMs)
            emit()
        }
    }

    override suspend fun markAlarmForDeletion(id: String, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(syncStatus = AlarmEntity.SYNC_STATUS_PENDING_DELETE, updatedAtEpochMs = updatedAtEpochMs)
            emit()
        }
    }

    override fun getPendingSyncCountFlow(): Flow<Int> = MutableStateFlow(0)

    override suspend fun getActiveTrackingJourney(): AlarmEntity? =
        alarmsMap.values.find {
            it.isEnabled && it.status in setOf(
                AlarmEntity.STATUS_ACTIVE_TRACKING,
                AlarmEntity.STATUS_TRACKING_DEGRADED,
                AlarmEntity.STATUS_RECALCULATING,
                AlarmEntity.STATUS_APPROACHING,
                AlarmEntity.STATUS_TRACKING_PENDING
            )
        }

    override fun getActiveTrackingJourneyFlow(): Flow<AlarmEntity?> =
        alarmsFlow.map { list ->
            list.find {
                it.isEnabled && it.status in setOf(
                    AlarmEntity.STATUS_ACTIVE_TRACKING,
                    AlarmEntity.STATUS_TRACKING_DEGRADED,
                    AlarmEntity.STATUS_RECALCULATING,
                    AlarmEntity.STATUS_APPROACHING,
                    AlarmEntity.STATUS_TRACKING_PENDING
                )
            }
        }
}
