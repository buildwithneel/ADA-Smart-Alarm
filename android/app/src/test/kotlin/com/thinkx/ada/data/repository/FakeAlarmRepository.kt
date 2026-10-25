package com.thinkx.ada.data.repository

import com.thinkx.ada.data.local.entity.AlarmEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map

class FakeAlarmRepository : AlarmRepository {

    val alarms = mutableMapOf<String, AlarmEntity>()
    val alarmsFlow = MutableStateFlow<List<AlarmEntity>>(emptyList())

    private fun emitUpdate() {
        alarmsFlow.value = alarms.values.toList()
    }

    override fun getAllAlarms(): Flow<List<AlarmEntity>> = alarmsFlow

    override fun getEnabledAlarmsFlow(): Flow<List<AlarmEntity>> =
        alarmsFlow.map { list -> list.filter { it.isEnabled } }

    override suspend fun getEnabledAlarms(): List<AlarmEntity> =
        alarms.values.filter { it.isEnabled }

    override suspend fun getAlarmById(id: String): AlarmEntity? = alarms[id]

    override fun getAlarmByIdFlow(id: String): Flow<AlarmEntity?> =
        alarmsFlow.map { list -> list.find { it.id == id } }

    override suspend fun getNextUpcomingAlarm(nowEpochMs: Long): AlarmEntity? =
        alarms.values
            .filter { it.isEnabled && it.scheduledAlarmEpochMs >= nowEpochMs }
            .minByOrNull { it.scheduledAlarmEpochMs }

    override fun getNextUpcomingAlarmFlow(nowEpochMs: Long): Flow<AlarmEntity?> =
        alarmsFlow.map { list ->
            list.filter { it.isEnabled && it.scheduledAlarmEpochMs >= nowEpochMs }
                .minByOrNull { it.scheduledAlarmEpochMs }
        }

    override suspend fun saveAlarm(alarm: AlarmEntity) {
        alarms[alarm.id] = alarm
        emitUpdate()
    }

    override suspend fun updateAlarm(alarm: AlarmEntity) {
        alarms[alarm.id] = alarm
        emitUpdate()
    }

    override suspend fun deleteAlarmById(id: String) {
        alarms.remove(id)
        emitUpdate()
    }

    override suspend fun setAlarmEnabled(id: String, isEnabled: Boolean) {
        alarms[id]?.let {
            alarms[id] = it.copy(isEnabled = isEnabled)
            emitUpdate()
        }
    }

    override suspend fun setAlarmStatus(id: String, status: String) {
        alarms[id]?.let {
            alarms[id] = it.copy(status = status)
            emitUpdate()
        }
    }

    override suspend fun snoozeAlarm(id: String, newScheduleEpochMs: Long) {
        alarms[id]?.let {
            alarms[id] = it.copy(
                scheduledAlarmEpochMs = newScheduleEpochMs,
                isSnoozed = true,
                snoozeCount = it.snoozeCount + 1,
                status = "SNOOZED"
            )
            emitUpdate()
        }
    }

    override suspend fun dismissAlarm(id: String) {
        alarms[id]?.let {
            alarms[id] = it.copy(
                isEnabled = false,
                status = "DISMISSED",
                isSnoozed = false
            )
            emitUpdate()
        }
    }
}
