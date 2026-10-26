package com.thinkx.ada.data.sync

import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.data.local.dao.AlarmDao
import com.thinkx.ada.data.local.dao.DestinationDao
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.local.entity.DestinationEntity
import com.thinkx.ada.network.api.AdaApiService
import com.thinkx.ada.network.dto.AlarmCreateDto
import com.thinkx.ada.network.dto.AlarmDto
import com.thinkx.ada.network.dto.AlarmUpdateDto
import com.thinkx.ada.network.dto.DestinationCreateDto
import com.thinkx.ada.util.DateTimeUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID

sealed interface SyncResult {
    data class Success(val pushedCount: Int, val pulledCount: Int) : SyncResult
    data class Failure(val message: String, val cause: Throwable? = null) : SyncResult
    data object Offline : SyncResult
}

sealed interface SyncState {
    data object Idle : SyncState
    data object Syncing : SyncState
    data class Success(val lastSyncedEpochMs: Long) : SyncState
    data class Error(val message: String) : SyncState
}

interface AlarmSyncRepository {
    val syncStateFlow: StateFlow<SyncState>
    val pendingSyncCountFlow: Flow<Int>

    suspend fun syncAlarms(): SyncResult
    suspend fun pushLocalAlarm(alarm: AlarmEntity): Result<AlarmEntity>
    suspend fun deleteRemoteAlarm(alarmId: String): Result<Unit>
}

class AlarmSyncRepositoryImpl(
    private val apiService: AdaApiService,
    private val alarmDao: AlarmDao,
    private val destinationDao: DestinationDao,
    private val alarmScheduler: AlarmScheduler
) : AlarmSyncRepository {

    private val _syncStateFlow = MutableStateFlow<SyncState>(SyncState.Idle)
    override val syncStateFlow: StateFlow<SyncState> = _syncStateFlow.asStateFlow()

    override val pendingSyncCountFlow: Flow<Int> = alarmDao.getPendingSyncCountFlow()

    override suspend fun syncAlarms(): SyncResult = withContext(Dispatchers.IO) {
        _syncStateFlow.value = SyncState.Syncing
        var pushedCount = 0
        var pulledCount = 0

        try {
            // 1. Process pending deletions
            val pendingDeletions = alarmDao.getAlarmsBySyncStatus(AlarmEntity.SYNC_STATUS_PENDING_DELETE)
            for (alarm in pendingDeletions) {
                val serverId = alarm.serverId
                if (serverId != null) {
                    try {
                        apiService.deleteAlarm(serverId)
                    } catch (e: Exception) {
                        // If 404 on server, it was already deleted remotely
                        if (!e.message.orEmpty().contains("404")) {
                            throw e
                        }
                    }
                }
                alarmDao.deleteAlarmById(alarm.id)
                pushedCount++
            }

            // 2. Process pending inserts and updates
            val pendingSync = alarmDao.getAlarmsBySyncStatus(AlarmEntity.SYNC_STATUS_PENDING)
            for (alarm in pendingSync) {
                val pushed = pushLocalAlarmInternal(alarm)
                if (pushed) pushedCount++
            }

            // 3. Pull remote alarms from backend
            val remoteAlarms = apiService.getAlarms()
            for (remote in remoteAlarms) {
                val updated = reconcileRemoteAlarm(remote)
                if (updated) pulledCount++
            }

            val now = System.currentTimeMillis()
            _syncStateFlow.value = SyncState.Success(now)
            SyncResult.Success(pushedCount, pulledCount)
        } catch (e: java.net.UnknownHostException) {
            _syncStateFlow.value = SyncState.Error("Network offline. Local alarms active.")
            SyncResult.Offline
        } catch (e: java.net.ConnectException) {
            _syncStateFlow.value = SyncState.Error("Server unreachable. Local alarms active.")
            SyncResult.Offline
        } catch (e: java.net.SocketTimeoutException) {
            _syncStateFlow.value = SyncState.Error("Connection timed out. Local alarms active.")
            SyncResult.Offline
        } catch (e: Exception) {
            val msg = e.localizedMessage ?: "Sync failed."
            _syncStateFlow.value = SyncState.Error(msg)
            SyncResult.Failure(msg, e)
        }
    }

    override suspend fun pushLocalAlarm(alarm: AlarmEntity): Result<AlarmEntity> = withContext(Dispatchers.IO) {
        try {
            val destServerId = ensureDestinationSynced(alarm)
            val serverId = alarm.serverId

            val resultAlarm = if (serverId == null) {
                // Create remotely using local ID as idempotency key
                val createDto = AlarmCreateDto(
                    title = alarm.title,
                    destinationId = destServerId,
                    arrivalTime = epochMsToTimeString(alarm.requiredArrivalEpochMs),
                    arrivalDate = epochMsToDateString(alarm.requiredArrivalEpochMs),
                    preparationTime = alarm.preparationDurationMinutes,
                    safetyBuffer = alarm.safetyBufferMinutes,
                    transportationMode = alarm.transportMode.lowercase(),
                    enabled = alarm.isEnabled,
                    originLat = alarm.originLat,
                    originLng = alarm.originLng
                )
                val response = apiService.createAlarm(createDto, idempotencyKey = alarm.id)
                val syncedAlarm = alarm.copy(
                    serverId = response.id,
                    syncStatus = AlarmEntity.SYNC_STATUS_SYNCED,
                    lastSyncedEpochMs = System.currentTimeMillis()
                )
                alarmDao.updateAlarm(syncedAlarm)
                syncedAlarm
            } else {
                // Update remotely
                val updateDto = AlarmUpdateDto(
                    title = alarm.title,
                    destinationId = destServerId,
                    arrivalTime = epochMsToTimeString(alarm.requiredArrivalEpochMs),
                    arrivalDate = epochMsToDateString(alarm.requiredArrivalEpochMs),
                    preparationTime = alarm.preparationDurationMinutes,
                    safetyBuffer = alarm.safetyBufferMinutes,
                    transportationMode = alarm.transportMode.lowercase(),
                    enabled = alarm.isEnabled
                )
                apiService.updateAlarm(serverId, updateDto)
                val syncedAlarm = alarm.copy(
                    syncStatus = AlarmEntity.SYNC_STATUS_SYNCED,
                    lastSyncedEpochMs = System.currentTimeMillis()
                )
                alarmDao.updateAlarm(syncedAlarm)
                syncedAlarm
            }
            Result.success(resultAlarm)
        } catch (e: Exception) {
            alarmDao.updateSyncStatus(
                id = alarm.id,
                serverId = alarm.serverId,
                syncStatus = AlarmEntity.SYNC_STATUS_PENDING,
                lastSyncedEpochMs = alarm.lastSyncedEpochMs ?: 0L
            )
            Result.failure(e)
        }
    }

    override suspend fun deleteRemoteAlarm(alarmId: String): Result<Unit> = withContext(Dispatchers.IO) {
        val alarm = alarmDao.getAlarmById(alarmId)
            ?: return@withContext Result.success(Unit)

        val serverId = alarm.serverId
        if (serverId == null) {
            // Never synced to server, delete locally immediately
            alarmDao.deleteAlarmById(alarmId)
            return@withContext Result.success(Unit)
        }

        try {
            apiService.deleteAlarm(serverId)
            alarmDao.deleteAlarmById(alarmId)
            Result.success(Unit)
        } catch (e: Exception) {
            // Mark for deletion on retry when network reconnects
            alarmDao.markAlarmForDeletion(alarmId, System.currentTimeMillis())
            Result.failure(e)
        }
    }

    private suspend fun pushLocalAlarmInternal(alarm: AlarmEntity): Boolean {
        val destServerId = try {
            ensureDestinationSynced(alarm)
        } catch (_: Exception) {
            return false
        }

        return try {
            if (alarm.serverId == null) {
                val createDto = AlarmCreateDto(
                    title = alarm.title,
                    destinationId = destServerId,
                    arrivalTime = epochMsToTimeString(alarm.requiredArrivalEpochMs),
                    arrivalDate = epochMsToDateString(alarm.requiredArrivalEpochMs),
                    preparationTime = alarm.preparationDurationMinutes,
                    safetyBuffer = alarm.safetyBufferMinutes,
                    transportationMode = alarm.transportMode.lowercase(),
                    enabled = alarm.isEnabled,
                    originLat = alarm.originLat,
                    originLng = alarm.originLng
                )
                val response = apiService.createAlarm(createDto, idempotencyKey = alarm.id)
                alarmDao.updateSyncStatus(
                    id = alarm.id,
                    serverId = response.id,
                    syncStatus = AlarmEntity.SYNC_STATUS_SYNCED,
                    lastSyncedEpochMs = System.currentTimeMillis()
                )
                true
            } else {
                val updateDto = AlarmUpdateDto(
                    title = alarm.title,
                    destinationId = destServerId,
                    arrivalTime = epochMsToTimeString(alarm.requiredArrivalEpochMs),
                    arrivalDate = epochMsToDateString(alarm.requiredArrivalEpochMs),
                    preparationTime = alarm.preparationDurationMinutes,
                    safetyBuffer = alarm.safetyBufferMinutes,
                    transportationMode = alarm.transportMode.lowercase(),
                    enabled = alarm.isEnabled
                )
                apiService.updateAlarm(alarm.serverId, updateDto)
                alarmDao.updateSyncStatus(
                    id = alarm.id,
                    serverId = alarm.serverId,
                    syncStatus = AlarmEntity.SYNC_STATUS_SYNCED,
                    lastSyncedEpochMs = System.currentTimeMillis()
                )
                true
            }
        } catch (_: Exception) {
            false
        }
    }

    private suspend fun reconcileRemoteAlarm(remote: AlarmDto): Boolean {
        val existingLocal = alarmDao.getAlarmByServerId(remote.id)
        if (existingLocal != null) {
            // If local has uncommitted pending edits, protect local edits
            if (existingLocal.syncStatus == AlarmEntity.SYNC_STATUS_PENDING ||
                existingLocal.syncStatus == AlarmEntity.SYNC_STATUS_PENDING_DELETE
            ) {
                return false
            }

            // Otherwise, update local entity from authoritative server state
            val updated = existingLocal.copy(
                title = remote.title,
                isEnabled = remote.enabled,
                travelDurationMinutes = remote.currentTravelMinutes ?: existingLocal.travelDurationMinutes,
                preparationDurationMinutes = remote.preparationTime,
                safetyBufferMinutes = remote.safetyBuffer,
                trafficDelayMinutes = remote.trafficDelayMinutes ?: existingLocal.trafficDelayMinutes,
                syncStatus = AlarmEntity.SYNC_STATUS_SYNCED,
                lastSyncedEpochMs = System.currentTimeMillis()
            )
            alarmDao.updateAlarm(updated)
            if (updated.isEnabled) {
                alarmScheduler.schedule(updated)
            } else {
                alarmScheduler.cancel(updated.id)
            }
            return true
        } else {
            // New remote alarm not yet on device: create and schedule locally
            val arrivalEpochMs = parseTimeToEpochMs(remote.arrivalTime)
            val wakeEpochMs = remote.calculatedWakeTime?.let { parseIsoToEpochMs(it) }
                ?: (arrivalEpochMs - (remote.preparationTime + remote.safetyBuffer + (remote.currentTravelMinutes ?: 30)) * 60_000L)

            val newLocal = AlarmEntity(
                id = UUID.randomUUID().toString(),
                serverId = remote.id,
                title = remote.title,
                destinationId = remote.destinationId,
                destinationName = remote.title,
                destinationAddress = "",
                destinationLat = remote.originLat ?: 0.0,
                destinationLng = remote.originLng ?: 0.0,
                requiredArrivalEpochMs = arrivalEpochMs,
                plannedArrivalEpochMs = arrivalEpochMs - remote.safetyBuffer * 60_000L,
                recommendedLeaveEpochMs = arrivalEpochMs - (remote.safetyBuffer + (remote.currentTravelMinutes ?: 30)) * 60_000L,
                recommendedWakeEpochMs = wakeEpochMs,
                scheduledAlarmEpochMs = wakeEpochMs,
                travelDurationMinutes = remote.currentTravelMinutes ?: 30,
                preparationDurationMinutes = remote.preparationTime,
                safetyBufferMinutes = remote.safetyBuffer,
                trafficDelayMinutes = remote.trafficDelayMinutes ?: 0,
                transportMode = remote.transportationMode.uppercase(),
                isEnabled = remote.enabled,
                syncStatus = AlarmEntity.SYNC_STATUS_SYNCED,
                lastSyncedEpochMs = System.currentTimeMillis()
            )
            alarmDao.insertAlarm(newLocal)
            if (newLocal.isEnabled && newLocal.scheduledAlarmEpochMs > System.currentTimeMillis()) {
                alarmScheduler.schedule(newLocal)
            }
            return true
        }
    }

    private suspend fun ensureDestinationSynced(alarm: AlarmEntity): String {
        if (!alarm.destinationId.isNullOrBlank()) {
            val dest = destinationDao.getDestinationById(alarm.destinationId)
            if (dest?.serverId != null) {
                return dest.serverId
            }
        }

        // Search existing remote destinations to prevent duplicates
        val remoteDestinations = apiService.getDestinations()
        val matched = remoteDestinations.firstOrNull {
            it.name.equals(alarm.destinationName, ignoreCase = true) ||
            (Math.abs(it.latitude - alarm.destinationLat) < 0.0001 && Math.abs(it.longitude - alarm.destinationLng) < 0.0001)
        }
        if (matched != null) {
            return matched.id
        }

        // Create destination remotely
        val newDestDto = apiService.createDestination(
            DestinationCreateDto(
                name = alarm.destinationName.ifBlank { "Destination" },
                address = alarm.destinationAddress.ifBlank { "Destination Address" },
                latitude = alarm.destinationLat,
                longitude = alarm.destinationLng
            )
        )
        return newDestDto.id
    }

    private fun epochMsToTimeString(epochMs: Long): String {
        val time = DateTimeUtils.epochMsToLocalDateTime(epochMs).toLocalTime()
        return time.format(DateTimeFormatter.ofPattern("HH:mm:ss"))
    }

    private fun epochMsToDateString(epochMs: Long): String {
        val date = DateTimeUtils.epochMsToLocalDateTime(epochMs).toLocalDate()
        return date.format(DateTimeFormatter.ISO_LOCAL_DATE)
    }

    private fun parseTimeToEpochMs(timeStr: String): Long {
        return try {
            val parts = timeStr.split(":")
            val h = parts[0].toInt()
            val m = parts[1].toInt()
            val s = if (parts.size > 2) parts[2].toInt() else 0
            val today = LocalDate.now()
            var dt = today.atTime(LocalTime.of(h, m, s))
            if (dt.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli() <= System.currentTimeMillis()) {
                dt = dt.plusDays(1)
            }
            dt.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
        } catch (_: Exception) {
            System.currentTimeMillis() + 3600_000L
        }
    }

    private fun parseIsoToEpochMs(isoStr: String): Long {
        return try {
            Instant.parse(isoStr).toEpochMilli()
        } catch (_: Exception) {
            System.currentTimeMillis()
        }
    }
}
