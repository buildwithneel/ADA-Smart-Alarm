package com.thinkx.ada.data.sync

import com.thinkx.ada.alarm.scheduler.FakeAlarmScheduler
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.network.dto.AlarmDto
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AlarmSyncRepositoryTest {

    private lateinit var fakeAlarmDao: FakeAlarmDao
    private lateinit var fakeDestinationDao: FakeDestinationDao
    private lateinit var fakeApiService: FakeAdaApiService
    private lateinit var fakeScheduler: FakeAlarmScheduler
    private lateinit var syncRepository: AlarmSyncRepositoryImpl

    private val baseNowEpochMs get() = System.currentTimeMillis()

    @Before
    fun setup() {
        fakeAlarmDao = FakeAlarmDao()
        fakeDestinationDao = FakeDestinationDao()
        fakeApiService = FakeAdaApiService()
        fakeScheduler = FakeAlarmScheduler(exactAlarmPermissionGranted = true, mockCurrentTimeEpochMs = baseNowEpochMs)

        syncRepository = AlarmSyncRepositoryImpl(
            apiService = fakeApiService,
            alarmDao = fakeAlarmDao,
            destinationDao = fakeDestinationDao,
            alarmScheduler = fakeScheduler
        )
    }

    private fun createLocalAlarm(
        id: String = "local-alarm-1",
        title: String = "Morning Commute",
        syncStatus: String = AlarmEntity.SYNC_STATUS_PENDING,
        serverId: String? = null
    ): AlarmEntity {
        val arrivalTime = baseNowEpochMs + 7200000L
        val wakeTime = baseNowEpochMs + 3600000L
        return AlarmEntity(
            id = id,
            serverId = serverId,
            syncStatus = syncStatus,
            title = title,
            destinationName = "Headquarters",
            destinationAddress = "1 Tech Way",
            destinationLat = 37.7749,
            destinationLng = -122.4194,
            requiredArrivalEpochMs = arrivalTime,
            plannedArrivalEpochMs = arrivalTime - 900000L,
            recommendedLeaveEpochMs = arrivalTime - 2700000L,
            recommendedWakeEpochMs = wakeTime,
            scheduledAlarmEpochMs = wakeTime,
            travelDurationMinutes = 30,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 15,
            isEnabled = true
        )
    }

    @Test
    fun syncAlarms_pushesPendingLocalAlarm_withIdempotencyKey() = runTest {
        val localAlarm = createLocalAlarm(id = "local-123", syncStatus = AlarmEntity.SYNC_STATUS_PENDING)
        fakeAlarmDao.insertAlarm(localAlarm)

        val result = syncRepository.syncAlarms()

        assertTrue(result is SyncResult.Success)
        val success = result as SyncResult.Success
        assertEquals(1, success.pushedCount)

        // Verify idempotency key was attached using local ID to protect against duplicates
        assertTrue(fakeApiService.capturedIdempotencyKeys.contains("local-123"))

        // Verify local alarm is updated to SYNCED and has serverId
        val updatedLocal = fakeAlarmDao.getAlarmById("local-123")
        assertNotNull(updatedLocal)
        assertEquals(AlarmEntity.SYNC_STATUS_SYNCED, updatedLocal!!.syncStatus)
        assertNotNull(updatedLocal.serverId)
    }

    @Test
    fun syncAlarms_pullsRemoteAlarms_andSchedulesLocally() = runTest {
        val remoteAlarm = AlarmDto(
            id = "server-uuid-999",
            destinationId = "dest-999",
            title = "Airport Trip",
            arrivalTime = "09:30:00",
            calculatedWakeTime = java.time.Instant.ofEpochMilli(baseNowEpochMs + 7200000L).toString(),
            preparationTime = 40,
            safetyBuffer = 20,
            currentTravelMinutes = 45,
            enabled = true
        )
        fakeApiService.serverAlarms.add(remoteAlarm)

        val result = syncRepository.syncAlarms()

        assertTrue(result is SyncResult.Success)
        val success = result as SyncResult.Success
        assertEquals(1, success.pulledCount)

        // Verify alarm inserted into local Room DAO with serverId
        val local = fakeAlarmDao.getAlarmByServerId("server-uuid-999")
        assertNotNull(local)
        assertEquals("Airport Trip", local!!.title)
        assertEquals(AlarmEntity.SYNC_STATUS_SYNCED, local.syncStatus)

        // Verify native alarm scheduler scheduled it
        assertTrue(fakeScheduler.scheduledAlarms.containsKey(local.id))
    }

    @Test
    fun syncAlarms_handlesNetworkOfflineGracefully_withoutAffectingLocalAlarms() = runTest {
        val localAlarm = createLocalAlarm(id = "local-offline-1")
        fakeAlarmDao.insertAlarm(localAlarm)
        fakeScheduler.schedule(localAlarm)

        fakeApiService.shouldFailWithNetworkError = true

        val result = syncRepository.syncAlarms()

        assertEquals(SyncResult.Offline, result)

        // Local alarm remains armed and scheduled locally!
        val retrieved = fakeAlarmDao.getAlarmById("local-offline-1")
        assertNotNull(retrieved)
        assertTrue(retrieved!!.isEnabled)
        assertTrue(fakeScheduler.scheduledAlarms.containsKey("local-offline-1"))
    }

    @Test
    fun syncAlarms_handlesTimeoutGracefully() = runTest {
        fakeApiService.shouldFailWithTimeout = true

        val result = syncRepository.syncAlarms()

        assertEquals(SyncResult.Offline, result)
        assertTrue(syncRepository.syncStateFlow.value is SyncState.Error)
    }

    @Test
    fun syncAlarms_doesNotOverwritePendingLocalEdits_withStaleRemoteData() = runTest {
        // Alarm already exists locally with serverId but has a pending local edit
        val localAlarm = createLocalAlarm(
            id = "local-conflict-1",
            title = "Locally Modified Title",
            syncStatus = AlarmEntity.SYNC_STATUS_PENDING,
            serverId = "server-uuid-555"
        )
        fakeAlarmDao.insertAlarm(localAlarm)

        // Server has stale title
        fakeApiService.serverAlarms.add(
            AlarmDto(
                id = "server-uuid-555",
                destinationId = "dest-1",
                title = "Stale Server Title",
                arrivalTime = "08:00:00"
            )
        )

        syncRepository.syncAlarms()

        // Local title must NOT be overwritten by stale server title
        val local = fakeAlarmDao.getAlarmById("local-conflict-1")
        assertNotNull(local)
        assertEquals("Locally Modified Title", local!!.title)
    }

    @Test
    fun deleteRemoteAlarm_offline_marksPendingDelete_andDeletesWhenOnline() = runTest {
        val alarm = createLocalAlarm(
            id = "alarm-to-delete",
            serverId = "server-uuid-delete",
            syncStatus = AlarmEntity.SYNC_STATUS_SYNCED
        )
        fakeAlarmDao.insertAlarm(alarm)
        fakeApiService.serverAlarms.add(
            AlarmDto(
                id = "server-uuid-delete",
                destinationId = "dest-1",
                title = "To Delete",
                arrivalTime = "10:00:00"
            )
        )

        // Delete while offline
        fakeApiService.shouldFailWithNetworkError = true
        val deleteResult = syncRepository.deleteRemoteAlarm("alarm-to-delete")
        assertTrue(deleteResult.isFailure)

        // Must be marked as PENDING_DELETE in Room
        val marked = fakeAlarmDao.getAlarmById("alarm-to-delete")
        assertNotNull(marked)
        assertEquals(AlarmEntity.SYNC_STATUS_PENDING_DELETE, marked!!.syncStatus)

        // Now network returns online -> run syncAlarms
        fakeApiService.shouldFailWithNetworkError = false
        val syncResult = syncRepository.syncAlarms()
        assertTrue(syncResult is SyncResult.Success)

        // Verified deleted from server and removed from Room
        assertTrue(fakeApiService.deletedAlarmIds.contains("server-uuid-delete"))
        val finalCheck = fakeAlarmDao.getAlarmById("alarm-to-delete")
        assertEquals(null, finalCheck)
    }
}
