package com.thinkx.ada.data.repository

import com.thinkx.ada.data.local.entity.AlarmEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf

class FakeAlarmRepository : AlarmRepository {

    val alarms = mutableMapOf<String, AlarmEntity>()

    override fun getAllAlarms(): Flow<List<AlarmEntity>> = flowOf(alarms.values.toList())

    override fun getEnabledAlarmsFlow(): Flow<List<AlarmEntity>> =
        flowOf(alarms.values.filter { it.isEnabled })

    override suspend fun getEnabledAlarms(): List<AlarmEntity> =
        alarms.values.filter { it.isEnabled }

    override suspend fun getAlarmById(id: String): AlarmEntity? = alarms[id]

    override fun getAlarmByIdFlow(id: String): Flow<AlarmEntity?> = flowOf(alarms[id])

    override suspend fun getNextUpcomingAlarm(nowEpochMs: Long): AlarmEntity? =
        alarms.values
            .filter { it.isEnabled && it.scheduledAlarmEpochMs >= nowEpochMs }
            .minByOrNull { it.scheduledAlarmEpochMs }

    override fun getNextUpcomingAlarmFlow(nowEpochMs: Long): Flow<AlarmEntity?> =
        kotlinx.coroutines.flow.flow { emit(getNextUpcomingAlarm(nowEpochMs)) }

    override suspend fun saveAlarm(alarm: AlarmEntity) {
        alarms[alarm.id] = alarm
    }

    override suspend fun updateAlarm(alarm: AlarmEntity) {
        alarms[alarm.id] = alarm
    }

    override suspend fun deleteAlarmById(id: String) {
        alarms.remove(id)
    }

    override suspend fun setAlarmEnabled(id: String, isEnabled: Boolean) {
        alarms[id]?.let { alarms[id] = it.copy(isEnabled = isEnabled) }
    }

    override suspend fun setAlarmStatus(id: String, status: String) {
        alarms[id]?.let { alarms[id] = it.copy(status = status) }
    }

    override suspend fun snoozeAlarm(id: String, newScheduleEpochMs: Long) {
        alarms[id]?.let {
            alarms[id] = it.copy(
                scheduledAlarmEpochMs = newScheduleEpochMs,
                isSnoozed = true,
                snoozeCount = it.snoozeCount + 1,
                status = "SNOOZED"
            )
        }
    }

    override suspend fun dismissAlarm(id: String) {
        alarms[id]?.let {
            alarms[id] = it.copy(
                isEnabled = false,
                status = "DISMISSED",
                isSnoozed = false
            )
        }
    }
}
