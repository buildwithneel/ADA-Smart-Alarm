package com.thinkx.ada.alarm.state

import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.repository.FakeAlarmRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AlarmStateTransitionTest {

    private lateinit var repository: FakeAlarmRepository
    private val now = 1700000000000L

    @Before
    fun setup() {
        repository = FakeAlarmRepository()
    }

    private fun createSampleAlarm(id: String = "test-alarm"): AlarmEntity {
        return AlarmEntity(
            id = id,
            title = "Morning Alarm",
            destinationName = "CHARUSAT",
            destinationAddress = "Changa, Gujarat",
            destinationLat = 22.5996,
            destinationLng = 72.8205,
            requiredArrivalEpochMs = now + 5400000L,
            plannedArrivalEpochMs = now + 4800000L,
            recommendedLeaveEpochMs = now + 2700000L,
            recommendedWakeEpochMs = now + 900000L,
            scheduledAlarmEpochMs = now + 900000L,
            travelDurationMinutes = 35,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            snoozeLengthMinutes = 10
        )
    }

    @Test
    fun `dismissing an active alarm marks isEnabled to false and status to DISMISSED`() = runBlocking {
        val alarm = createSampleAlarm()
        repository.saveAlarm(alarm)

        repository.dismissAlarm(alarm.id)

        val updated = repository.getAlarmById(alarm.id)
        requireNotNull(updated)
        assertFalse(updated.isEnabled)
        assertEquals(AlarmEntity.STATUS_DISMISSED, updated.status)
        assertFalse(updated.isSnoozed)
    }

    @Test
    fun `snoozing an active alarm sets status to SNOOZED, increments count, and sets future schedule`() = runBlocking {
        val alarm = createSampleAlarm()
        repository.saveAlarm(alarm)

        val snoozeScheduleEpochMs = now + (10 * 60 * 1000L) // +10 minutes
        repository.snoozeAlarm(alarm.id, snoozeScheduleEpochMs)

        val updated = repository.getAlarmById(alarm.id)
        requireNotNull(updated)
        assertTrue(updated.isEnabled)
        assertTrue(updated.isSnoozed)
        assertEquals(1, updated.snoozeCount)
        assertEquals(AlarmEntity.STATUS_SNOOZED, updated.status)
        assertEquals(snoozeScheduleEpochMs, updated.scheduledAlarmEpochMs)

        // Second snooze
        val secondSnoozeEpochMs = snoozeScheduleEpochMs + (10 * 60 * 1000L)
        repository.snoozeAlarm(alarm.id, secondSnoozeEpochMs)

        val doubleSnoozed = repository.getAlarmById(alarm.id)
        requireNotNull(doubleSnoozed)
        assertEquals(2, doubleSnoozed.snoozeCount)
        assertEquals(secondSnoozeEpochMs, doubleSnoozed.scheduledAlarmEpochMs)
    }

    @Test
    fun `toggling alarm enabled state updates flag correctly`() = runBlocking {
        val alarm = createSampleAlarm()
        repository.saveAlarm(alarm)
        assertTrue(repository.getAlarmById(alarm.id)!!.isEnabled)

        repository.setAlarmEnabled(alarm.id, false)
        assertFalse(repository.getAlarmById(alarm.id)!!.isEnabled)

        repository.setAlarmEnabled(alarm.id, true)
        assertTrue(repository.getAlarmById(alarm.id)!!.isEnabled)
    }
}
