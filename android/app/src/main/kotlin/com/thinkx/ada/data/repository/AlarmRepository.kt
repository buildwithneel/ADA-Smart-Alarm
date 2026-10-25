package com.thinkx.ada.data.repository

import com.thinkx.ada.data.local.dao.AlarmDao
import com.thinkx.ada.data.local.entity.AlarmEntity
import kotlinx.coroutines.flow.Flow

interface AlarmRepository {
    fun getAllAlarms(): Flow<List<AlarmEntity>>
    fun getEnabledAlarmsFlow(): Flow<List<AlarmEntity>>
    suspend fun getEnabledAlarms(): List<AlarmEntity>
    suspend fun getAlarmById(id: String): AlarmEntity?
    fun getAlarmByIdFlow(id: String): Flow<AlarmEntity?>
    suspend fun getNextUpcomingAlarm(nowEpochMs: Long = System.currentTimeMillis()): AlarmEntity?
    fun getNextUpcomingAlarmFlow(nowEpochMs: Long = System.currentTimeMillis()): Flow<AlarmEntity?>
    suspend fun saveAlarm(alarm: AlarmEntity)
    suspend fun updateAlarm(alarm: AlarmEntity)
    suspend fun deleteAlarmById(id: String)
    suspend fun setAlarmEnabled(id: String, isEnabled: Boolean)
    suspend fun setAlarmStatus(id: String, status: String)
    suspend fun snoozeAlarm(id: String, newScheduleEpochMs: Long)
    suspend fun dismissAlarm(id: String)
}

class AlarmRepositoryImpl(
    private val alarmDao: AlarmDao
) : AlarmRepository {

    override fun getAllAlarms(): Flow<List<AlarmEntity>> = alarmDao.getAllAlarms()

    override fun getEnabledAlarmsFlow(): Flow<List<AlarmEntity>> = alarmDao.getEnabledAlarmsFlow()

    override suspend fun getEnabledAlarms(): List<AlarmEntity> = alarmDao.getEnabledAlarms()

    override suspend fun getAlarmById(id: String): AlarmEntity? = alarmDao.getAlarmById(id)

    override fun getAlarmByIdFlow(id: String): Flow<AlarmEntity?> = alarmDao.getAlarmByIdFlow(id)

    override suspend fun getNextUpcomingAlarm(nowEpochMs: Long): AlarmEntity? =
        alarmDao.getNextUpcomingAlarm(nowEpochMs)

    override fun getNextUpcomingAlarmFlow(nowEpochMs: Long): Flow<AlarmEntity?> =
        alarmDao.getNextUpcomingAlarmFlow(nowEpochMs)

    override suspend fun saveAlarm(alarm: AlarmEntity) = alarmDao.insertAlarm(alarm)

    override suspend fun updateAlarm(alarm: AlarmEntity) = alarmDao.updateAlarm(alarm)

    override suspend fun deleteAlarmById(id: String) = alarmDao.deleteAlarmById(id)

    override suspend fun setAlarmEnabled(id: String, isEnabled: Boolean) =
        alarmDao.updateAlarmEnabled(id, isEnabled, System.currentTimeMillis())

    override suspend fun setAlarmStatus(id: String, status: String) =
        alarmDao.updateAlarmStatus(id, status, System.currentTimeMillis())

    override suspend fun snoozeAlarm(id: String, newScheduleEpochMs: Long) =
        alarmDao.snoozeAlarm(id, newScheduleEpochMs, System.currentTimeMillis())

    override suspend fun dismissAlarm(id: String) =
        alarmDao.dismissOneTimeAlarm(id, System.currentTimeMillis())
}
