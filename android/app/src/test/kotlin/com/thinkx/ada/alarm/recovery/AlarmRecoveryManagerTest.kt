package com.thinkx.ada.alarm.recovery

import com.thinkx.ada.alarm.scheduler.FakeAlarmScheduler
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.repository.FakeAlarmRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AlarmRecoveryManagerTest {

    private lateinit var repository: FakeAlarmRepository
    private lateinit var scheduler: FakeAlarmScheduler
    private lateinit var journeyScheduler: com.thinkx.ada.journey.FakeJourneyScheduler
    private lateinit var recoveryManager: AlarmRecoveryManager

    private val nowEpochMs = 1700000000000L

    @Before
    fun setup() {
        repository = FakeAlarmRepository()
        scheduler = FakeAlarmScheduler(
            exactAlarmPermissionGranted = true,
            mockCurrentTimeEpochMs = nowEpochMs
        )
        journeyScheduler = com.thinkx.ada.journey.FakeJourneyScheduler(
            exactAlarmPermissionGranted = true
        )
        recoveryManager = AlarmRecoveryManager(repository, scheduler, journeyScheduler)
    }

    private fun createAlarm(
        id: String,
        scheduledEpochMs: Long,
        isEnabled: Boolean = true,
        repeatMask: Int = 0
    ): AlarmEntity {
        return AlarmEntity(
            id = id,
            title = "Alarm $id",
            destinationName = "Work",
            destinationAddress = "Station Road",
            destinationLat = 22.5,
            destinationLng = 72.8,
            requiredArrivalEpochMs = scheduledEpochMs + 3600000L,
            plannedArrivalEpochMs = scheduledEpochMs + 3000000L,
            recommendedLeaveEpochMs = scheduledEpochMs + 1800000L,
            recommendedWakeEpochMs = scheduledEpochMs,
            scheduledAlarmEpochMs = scheduledEpochMs,
            travelDurationMinutes = 20,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            isEnabled = isEnabled,
            repeatDaysMask = repeatMask
        )
    }

    @Test
    fun `recovery re-arms eligible future alarms and marks past alarms as dismissed`() = runBlocking {
        // Alarm 1: Future alarm (+2h)
        val futureAlarm = createAlarm("future-1", nowEpochMs + 7200000L)
        // Alarm 2: Past one-time alarm (-1h)
        val pastOneTime = createAlarm("past-1", nowEpochMs - 3600000L)
        // Alarm 3: Disabled alarm
        val disabledAlarm = createAlarm("disabled-1", nowEpochMs + 3600000L, isEnabled = false)

        repository.saveAlarm(futureAlarm)
        repository.saveAlarm(pastOneTime)
        repository.saveAlarm(disabledAlarm)

        val result = recoveryManager.rearmAllEligibleAlarms(nowEpochMs)

        // 2 enabled alarms checked
        assertEquals(2, result.totalChecked)
        assertEquals(1, result.rearmedCount)
        assertEquals(1, result.expiredCount)
        assertEquals(0, result.failureCount)

        // Future alarm was scheduled
        assertTrue(scheduler.scheduledAlarms.containsKey("future-1"))

        // Past one-time alarm was marked as dismissed in repository
        assertFalse(repository.alarms["past-1"]!!.isEnabled)
        assertEquals(AlarmEntity.STATUS_DISMISSED, repository.alarms["past-1"]!!.status)

        // Disabled alarm was not touched
        assertFalse(scheduler.scheduledAlarms.containsKey("disabled-1"))
    }

    @Test
    fun `recovery aborts gracefully when exact alarm permission is missing`() = runBlocking {
        scheduler.exactAlarmPermissionGranted = false
        val futureAlarm = createAlarm("future-1", nowEpochMs + 3600000L)
        repository.saveAlarm(futureAlarm)

        val result = recoveryManager.rearmAllEligibleAlarms(nowEpochMs)

        assertEquals(0, result.rearmedCount)
        assertEquals(0, scheduler.scheduledAlarms.size)
    }

    @Test
    fun `re-arming multiple future alarms is idempotent and avoids duplicates`() = runBlocking {
        val alarm1 = createAlarm("alarm-1", nowEpochMs + 1800000L)
        val alarm2 = createAlarm("alarm-2", nowEpochMs + 3600000L)
        repository.saveAlarm(alarm1)
        repository.saveAlarm(alarm2)

        val run1 = recoveryManager.rearmAllEligibleAlarms(nowEpochMs)
        assertEquals(2, run1.rearmedCount)
        assertEquals(2, scheduler.scheduledAlarms.size)

        // Second run re-arms same keys without expanding collection
        val run2 = recoveryManager.rearmAllEligibleAlarms(nowEpochMs)
        assertEquals(2, run2.rearmedCount)
        assertEquals(2, scheduler.scheduledAlarms.size)
    }

    @Test
    fun `recovery re-arms journey tracking start for future journeys`() = runBlocking {
        // Departure in 60 mins, tracking lead 15 mins -> tracking start in 45 mins
        val futureJourney = createAlarm("journey-future", nowEpochMs + 3600000L).copy(
            scheduledDepartureEpochMs = nowEpochMs + 3600000L,
            trackingLeadMinutes = 15
        )
        repository.saveAlarm(futureJourney)

        val result = recoveryManager.rearmAllEligibleAlarms(nowEpochMs)

        assertEquals(1, result.rearmedCount)
        assertTrue("Alarm scheduler has journey", scheduler.scheduledAlarms.containsKey("journey-future"))
        assertTrue("Journey scheduler has journey", journeyScheduler.scheduledJourneys.containsKey("journey-future"))
    }

    @Test
    fun `recovery stops expired active journeys that ran past arrival time by more than 2 hours`() = runBlocking {
        // Required arrival was 3 hours ago, but was left in ACTIVE_TRACKING
        val expiredJourney = createAlarm("journey-expired", nowEpochMs - 14400000L).copy(
            requiredArrivalEpochMs = nowEpochMs - 10800000L, // 3 hours ago
            status = AlarmEntity.STATUS_ACTIVE_TRACKING
        )
        repository.saveAlarm(expiredJourney)

        val result = recoveryManager.rearmAllEligibleAlarms(nowEpochMs)

        assertEquals(1, result.expiredCount)
        assertEquals(AlarmEntity.STATUS_STOPPED, repository.alarms["journey-expired"]!!.status)
        assertFalse(repository.alarms["journey-expired"]!!.isEnabled)
    }
}
