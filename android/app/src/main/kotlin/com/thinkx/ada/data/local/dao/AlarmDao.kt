package com.thinkx.ada.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.thinkx.ada.data.local.entity.AlarmEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface AlarmDao {

    @Query("SELECT * FROM alarms ORDER BY scheduledAlarmEpochMs ASC")
    fun getAllAlarms(): Flow<List<AlarmEntity>>

    @Query("SELECT * FROM alarms WHERE isEnabled = 1 ORDER BY scheduledAlarmEpochMs ASC")
    suspend fun getEnabledAlarms(): List<AlarmEntity>

    @Query("SELECT * FROM alarms WHERE isEnabled = 1 ORDER BY scheduledAlarmEpochMs ASC")
    fun getEnabledAlarmsFlow(): Flow<List<AlarmEntity>>

    @Query("SELECT * FROM alarms WHERE id = :id LIMIT 1")
    suspend fun getAlarmById(id: String): AlarmEntity?

    @Query("SELECT * FROM alarms WHERE id = :id LIMIT 1")
    fun getAlarmByIdFlow(id: String): Flow<AlarmEntity?>

    @Query("SELECT * FROM alarms WHERE isEnabled = 1 AND scheduledAlarmEpochMs >= :nowEpochMs ORDER BY scheduledAlarmEpochMs ASC LIMIT 1")
    suspend fun getNextUpcomingAlarm(nowEpochMs: Long): AlarmEntity?

    @Query("SELECT * FROM alarms WHERE isEnabled = 1 AND scheduledAlarmEpochMs >= :nowEpochMs ORDER BY scheduledAlarmEpochMs ASC LIMIT 1")
    fun getNextUpcomingAlarmFlow(nowEpochMs: Long): Flow<AlarmEntity?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAlarm(alarm: AlarmEntity)

    @Update
    suspend fun updateAlarm(alarm: AlarmEntity)

    @Delete
    suspend fun deleteAlarm(alarm: AlarmEntity)

    @Query("DELETE FROM alarms WHERE id = :id")
    suspend fun deleteAlarmById(id: String)

    @Query("UPDATE alarms SET isEnabled = :isEnabled, updatedAtEpochMs = :updatedAtEpochMs WHERE id = :id")
    suspend fun updateAlarmEnabled(id: String, isEnabled: Boolean, updatedAtEpochMs: Long)

    @Query("UPDATE alarms SET status = :status, updatedAtEpochMs = :updatedAtEpochMs WHERE id = :id")
    suspend fun updateAlarmStatus(id: String, status: String, updatedAtEpochMs: Long)

    @Query("UPDATE alarms SET scheduledAlarmEpochMs = :newScheduleEpochMs, isSnoozed = 1, snoozeCount = snoozeCount + 1, status = 'SNOOZED', updatedAtEpochMs = :updatedAtEpochMs WHERE id = :id")
    suspend fun snoozeAlarm(id: String, newScheduleEpochMs: Long, updatedAtEpochMs: Long)

    @Query("UPDATE alarms SET isEnabled = 0, status = 'DISMISSED', isSnoozed = 0, updatedAtEpochMs = :updatedAtEpochMs WHERE id = :id")
    suspend fun dismissOneTimeAlarm(id: String, updatedAtEpochMs: Long)
}
