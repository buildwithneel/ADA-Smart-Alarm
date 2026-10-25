package com.thinkx.ada.alarm.scheduler

import com.thinkx.ada.data.local.entity.AlarmEntity

sealed interface ScheduleResult {
    data class Success(val scheduledEpochMs: Long, val alarmId: String) : ScheduleResult
    data object PermissionDenied : ScheduleResult
    data class PastTime(val scheduledEpochMs: Long, val currentEpochMs: Long) : ScheduleResult
    data class Error(val message: String, val cause: Throwable? = null) : ScheduleResult
}

interface AlarmScheduler {
    fun schedule(alarm: AlarmEntity): ScheduleResult
    fun cancel(alarmId: String): Boolean
    fun canScheduleExactAlarms(): Boolean
}
