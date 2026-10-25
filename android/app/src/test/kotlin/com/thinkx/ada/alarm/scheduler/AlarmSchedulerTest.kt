package com.thinkx.ada.alarm.scheduler

import com.thinkx.ada.data.local.entity.AlarmEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AlarmSchedulerTest {

    private lateinit var scheduler: FakeAlarmScheduler
    private val baselineNow = 1700000000000L // Reference epoch ms

    @Before
    fun setup() {
        scheduler = FakeAlarmScheduler(
            exactAlarmPermissionGranted = true,
            mockCurrentTimeEpochMs = baselineNow
        )
    }

    private fun createAlarm(
        id: String = "alarm-001",
        scheduledTime: Long = baselineNow + 3600000L, // 1 hour in future
        isEnabled: Boolean = true
    ): AlarmEntity {
        return AlarmEntity(
            id = id,
            title = "Work commute",
            destinationName = "Office",
            destinationAddress = "123 Tech Park",
            destinationLat = 22.5,
            destinationLng = 72.8,
            requiredArrivalEpochMs = scheduledTime + 3600000L,
            plannedArrivalEpochMs = scheduledTime + 3000000L,
            recommendedLeaveEpochMs = scheduledTime + 1800000L,
            recommendedWakeEpochMs = scheduledTime,
            scheduledAlarmEpochMs = scheduledTime,
            travelDurationMinutes = 20,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            isEnabled = isEnabled
        )
    }

    @Test
    fun `successful scheduling stores alarm and returns success result`() {
        val alarm = createAlarm()
        val result = scheduler.schedule(alarm)

        assertTrue(result is ScheduleResult.Success)
        val success = result as ScheduleResult.Success
        assertEquals(alarm.scheduledAlarmEpochMs, success.scheduledEpochMs)
        assertEquals(alarm.id, success.alarmId)
        assertTrue(scheduler.scheduledAlarms.containsKey(alarm.id))
    }

    @Test
    fun `permission denied returns ScheduleResult_PermissionDenied`() {
        scheduler.exactAlarmPermissionGranted = false
        val alarm = createAlarm()

        val result = scheduler.schedule(alarm)
        assertEquals(ScheduleResult.PermissionDenied, result)
        assertFalse(scheduler.scheduledAlarms.containsKey(alarm.id))
    }

    @Test
    fun `past alarm time is rejected with ScheduleResult_PastTime`() {
        val pastAlarm = createAlarm(scheduledTime = baselineNow - 5000L) // 5 seconds in past

        val result = scheduler.schedule(pastAlarm)
        assertTrue(result is ScheduleResult.PastTime)
        val past = result as ScheduleResult.PastTime
        assertEquals(pastAlarm.scheduledAlarmEpochMs, past.scheduledEpochMs)
        assertEquals(baselineNow, past.currentEpochMs)
        assertFalse(scheduler.scheduledAlarms.containsKey(pastAlarm.id))
    }

    @Test
    fun `disabled alarm cancels existing schedule and returns success`() {
        val alarm = createAlarm()
        scheduler.schedule(alarm)
        assertTrue(scheduler.scheduledAlarms.containsKey(alarm.id))

        val disabledAlarm = alarm.copy(isEnabled = false)
        val result = scheduler.schedule(disabledAlarm)

        assertTrue(result is ScheduleResult.Success)
        assertNull(scheduler.scheduledAlarms[alarm.id])
        assertTrue(scheduler.cancelledAlarmIds.contains(alarm.id))
    }

    @Test
    fun `rescheduling after edit replaces existing schedule with new timestamp`() {
        val initialAlarm = createAlarm(scheduledTime = baselineNow + 1800000L) // 30 min
        scheduler.schedule(initialAlarm)

        val updatedAlarm = initialAlarm.copy(
            scheduledAlarmEpochMs = baselineNow + 3600000L // Shifted to 60 min
        )
        val result = scheduler.schedule(updatedAlarm)

        assertTrue(result is ScheduleResult.Success)
        assertEquals(1, scheduler.scheduledAlarms.size)
        assertEquals(baselineNow + 3600000L, scheduler.scheduledAlarms[initialAlarm.id]?.scheduledAlarmEpochMs)
    }

    @Test
    fun `cancel removes alarm from scheduler and records cancellation`() {
        val alarm = createAlarm()
        scheduler.schedule(alarm)
        assertTrue(scheduler.scheduledAlarms.containsKey(alarm.id))

        val cancelled = scheduler.cancel(alarm.id)
        assertTrue(cancelled)
        assertFalse(scheduler.scheduledAlarms.containsKey(alarm.id))
        assertTrue(scheduler.cancelledAlarmIds.contains(alarm.id))
    }
}
