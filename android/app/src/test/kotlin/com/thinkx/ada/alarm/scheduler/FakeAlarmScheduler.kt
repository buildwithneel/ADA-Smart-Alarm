package com.thinkx.ada.alarm.scheduler

import com.thinkx.ada.data.local.entity.AlarmEntity

/**
 * Deterministic in-memory fake implementation of [AlarmScheduler] for isolated unit testing.
 */
class FakeAlarmScheduler(
    var exactAlarmPermissionGranted: Boolean = true,
    var mockCurrentTimeEpochMs: Long = System.currentTimeMillis()
) : AlarmScheduler {

    val scheduledAlarms = mutableMapOf<String, AlarmEntity>()
    val cancelledAlarmIds = mutableListOf<String>()

    override fun canScheduleExactAlarms(): Boolean = exactAlarmPermissionGranted

    override fun schedule(alarm: AlarmEntity): ScheduleResult {
        if (!alarm.isEnabled) {
            cancel(alarm.id)
            return ScheduleResult.Success(alarm.scheduledAlarmEpochMs, alarm.id)
        }

        if (!canScheduleExactAlarms()) {
            return ScheduleResult.PermissionDenied
        }

        if (alarm.scheduledAlarmEpochMs <= mockCurrentTimeEpochMs) {
            return ScheduleResult.PastTime(alarm.scheduledAlarmEpochMs, mockCurrentTimeEpochMs)
        }

        scheduledAlarms[alarm.id] = alarm
        return ScheduleResult.Success(alarm.scheduledAlarmEpochMs, alarm.id)
    }

    override fun cancel(alarmId: String): Boolean {
        cancelledAlarmIds.add(alarmId)
        scheduledAlarms.remove(alarmId)
        return true
    }

    fun clear() {
        scheduledAlarms.clear()
        cancelledAlarmIds.clear()
    }
}
