package com.thinkx.ada.data.sync

import com.thinkx.ada.data.local.dao.AlarmDao
import com.thinkx.ada.data.local.dao.DestinationDao
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.local.entity.DestinationEntity
import com.thinkx.ada.network.api.AdaApiService
import com.thinkx.ada.network.dto.AlarmCreateDto
import com.thinkx.ada.network.dto.AlarmDto
import com.thinkx.ada.network.dto.AlarmUpdateDto
import com.thinkx.ada.network.dto.DestinationCreateDto
import com.thinkx.ada.network.dto.DestinationDto
import com.thinkx.ada.network.dto.UserDto
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map
import retrofit2.Response
import java.util.UUID

class FakeAlarmDao(
    initialAlarms: List<AlarmEntity> = emptyList()
) : AlarmDao {
    private val alarmsMap = mutableMapOf<String, AlarmEntity>().apply {
        initialAlarms.forEach { put(it.id, it) }
    }
    private val alarmsFlow = MutableStateFlow(initialAlarms)

    private fun emit() {
        alarmsFlow.value = alarmsMap.values.toList()
    }

    override fun getAllAlarms(): Flow<List<AlarmEntity>> = alarmsFlow

    override suspend fun getEnabledAlarms(): List<AlarmEntity> =
        alarmsMap.values.filter { it.isEnabled }

    override fun getEnabledAlarmsFlow(): Flow<List<AlarmEntity>> =
        alarmsFlow.map { list -> list.filter { it.isEnabled } }

    override suspend fun getAlarmById(id: String): AlarmEntity? = alarmsMap[id]

    override fun getAlarmByIdFlow(id: String): Flow<AlarmEntity?> =
        alarmsFlow.map { it.find { a -> a.id == id } }

    override suspend fun getNextUpcomingAlarm(nowEpochMs: Long): AlarmEntity? =
        alarmsMap.values.filter { it.isEnabled && it.scheduledAlarmEpochMs >= nowEpochMs }
            .minByOrNull { it.scheduledAlarmEpochMs }

    override fun getNextUpcomingAlarmFlow(nowEpochMs: Long): Flow<AlarmEntity?> =
        alarmsFlow.map { list ->
            list.filter { it.isEnabled && it.scheduledAlarmEpochMs >= nowEpochMs }
                .minByOrNull { it.scheduledAlarmEpochMs }
        }

    override suspend fun insertAlarm(alarm: AlarmEntity) {
        alarmsMap[alarm.id] = alarm
        emit()
    }

    override suspend fun updateAlarm(alarm: AlarmEntity) {
        alarmsMap[alarm.id] = alarm
        emit()
    }

    override suspend fun deleteAlarm(alarm: AlarmEntity) {
        alarmsMap.remove(alarm.id)
        emit()
    }

    override suspend fun deleteAlarmById(id: String) {
        alarmsMap.remove(id)
        emit()
    }

    override suspend fun updateAlarmEnabled(id: String, isEnabled: Boolean, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(isEnabled = isEnabled, updatedAtEpochMs = updatedAtEpochMs)
            emit()
        }
    }

    override suspend fun updateAlarmStatus(id: String, status: String, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(status = status, updatedAtEpochMs = updatedAtEpochMs)
            emit()
        }
    }

    override suspend fun snoozeAlarm(id: String, newScheduleEpochMs: Long, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(
                scheduledAlarmEpochMs = newScheduleEpochMs,
                isSnoozed = true,
                snoozeCount = it.snoozeCount + 1,
                status = AlarmEntity.STATUS_SNOOZED,
                updatedAtEpochMs = updatedAtEpochMs
            )
            emit()
        }
    }

    override suspend fun dismissOneTimeAlarm(id: String, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(
                isEnabled = false,
                status = AlarmEntity.STATUS_DISMISSED,
                isSnoozed = false,
                updatedAtEpochMs = updatedAtEpochMs
            )
            emit()
        }
    }

    override suspend fun getAlarmsBySyncStatus(status: String): List<AlarmEntity> =
        alarmsMap.values.filter { it.syncStatus == status }

    override suspend fun getAlarmByServerId(serverId: String): AlarmEntity? =
        alarmsMap.values.firstOrNull { it.serverId == serverId }

    override suspend fun updateSyncStatus(
        id: String,
        serverId: String?,
        syncStatus: String,
        lastSyncedEpochMs: Long
    ) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(
                serverId = serverId ?: it.serverId,
                syncStatus = syncStatus,
                lastSyncedEpochMs = lastSyncedEpochMs
            )
            emit()
        }
    }

    override suspend fun markAlarmForDeletion(id: String, updatedAtEpochMs: Long) {
        alarmsMap[id]?.let {
            alarmsMap[id] = it.copy(
                syncStatus = AlarmEntity.SYNC_STATUS_PENDING_DELETE,
                updatedAtEpochMs = updatedAtEpochMs
            )
            emit()
        }
    }

    override fun getPendingSyncCountFlow(): Flow<Int> =
        alarmsFlow.map { list -> list.count { it.syncStatus != AlarmEntity.SYNC_STATUS_SYNCED } }

    override suspend fun getActiveTrackingJourney(): AlarmEntity? =
        alarmsMap.values.find {
            it.isEnabled && it.status in setOf(
                AlarmEntity.STATUS_ACTIVE_TRACKING,
                AlarmEntity.STATUS_TRACKING_DEGRADED,
                AlarmEntity.STATUS_RECALCULATING,
                AlarmEntity.STATUS_APPROACHING
            )
        }

    override fun getActiveTrackingJourneyFlow(): Flow<AlarmEntity?> =
        alarmsFlow.map { list ->
            list.find {
                it.isEnabled && it.status in setOf(
                    AlarmEntity.STATUS_ACTIVE_TRACKING,
                    AlarmEntity.STATUS_TRACKING_DEGRADED,
                    AlarmEntity.STATUS_RECALCULATING,
                    AlarmEntity.STATUS_APPROACHING
                )
            }
        }
}

class FakeDestinationDao(
    initialDestinations: List<DestinationEntity> = emptyList()
) : DestinationDao {
    private val destMap = mutableMapOf<String, DestinationEntity>().apply {
        initialDestinations.forEach { put(it.id, it) }
    }
    private val destFlow = MutableStateFlow(initialDestinations)

    private fun emit() {
        destFlow.value = destMap.values.toList()
    }

    override fun getSavedDestinations(): Flow<List<DestinationEntity>> =
        destFlow.map { list -> list.filter { it.isSaved } }

    override fun getRecentDestinations(limit: Int): Flow<List<DestinationEntity>> =
        destFlow.map { list -> list.filter { it.isRecent }.take(limit) }

    override suspend fun getDestinationById(id: String): DestinationEntity? = destMap[id]

    override suspend fun insertDestination(destination: DestinationEntity) {
        destMap[destination.id] = destination
        emit()
    }

    override suspend fun updateDestination(destination: DestinationEntity) {
        destMap[destination.id] = destination
        emit()
    }

    override suspend fun deleteDestination(destination: DestinationEntity) {
        destMap.remove(destination.id)
        emit()
    }

    override suspend fun deleteDestinationById(id: String) {
        destMap.remove(id)
        emit()
    }

    override suspend fun getDestinationByServerId(serverId: String): DestinationEntity? =
        destMap.values.firstOrNull { it.serverId == serverId }

    override suspend fun getUnsyncedDestinations(): List<DestinationEntity> =
        destMap.values.filter { !it.isSynced }

    override suspend fun updateDestinationSyncStatus(id: String, serverId: String) {
        destMap[id]?.let {
            destMap[id] = it.copy(serverId = serverId, isSynced = true)
            emit()
        }
    }
}

class FakeAdaApiService : AdaApiService {
    val serverAlarms = mutableListOf<AlarmDto>()
    val serverDestinations = mutableListOf<DestinationDto>()
    var shouldFailWithNetworkError = false
    var shouldFailWithTimeout = false
    val createdAlarms = mutableListOf<AlarmCreateDto>()
    val updatedAlarms = mutableListOf<Pair<String, AlarmUpdateDto>>()
    val deletedAlarmIds = mutableListOf<String>()
    val capturedIdempotencyKeys = mutableListOf<String?>()

    override suspend fun getCurrentUser(): UserDto {
        return UserDto(id = "user-uuid-1", email = "test@ada.com", name = "Test User")
    }

    override suspend fun getDestinations(skip: Int, limit: Int): List<DestinationDto> {
        checkNetwork()
        return serverDestinations
    }

    override suspend fun createDestination(body: DestinationCreateDto): DestinationDto {
        checkNetwork()
        val dest = DestinationDto(
            id = "server-dest-${UUID.randomUUID()}",
            name = body.name,
            address = body.address,
            latitude = body.latitude,
            longitude = body.longitude
        )
        serverDestinations.add(dest)
        return dest
    }

    override suspend fun getDestination(id: String): DestinationDto {
        checkNetwork()
        return serverDestinations.first { it.id == id }
    }

    override suspend fun deleteDestination(id: String): Response<Unit> {
        checkNetwork()
        serverDestinations.removeAll { it.id == id }
        return Response.success(Unit)
    }

    override suspend fun getAlarms(
        status: String?,
        filter: String?,
        skip: Int,
        limit: Int
    ): List<AlarmDto> {
        checkNetwork()
        return serverAlarms
    }

    override suspend fun createAlarm(
        body: AlarmCreateDto,
        idempotencyKey: String?
    ): AlarmDto {
        checkNetwork()
        capturedIdempotencyKeys.add(idempotencyKey)
        createdAlarms.add(body)
        val alarm = AlarmDto(
            id = "server-alarm-${UUID.randomUUID()}",
            destinationId = body.destinationId,
            title = body.title,
            arrivalTime = body.arrivalTime,
            preparationTime = body.preparationTime,
            safetyBuffer = body.safetyBuffer,
            transportationMode = body.transportationMode,
            enabled = body.enabled
        )
        serverAlarms.add(alarm)
        return alarm
    }

    override suspend fun getAlarm(id: String): AlarmDto {
        checkNetwork()
        return serverAlarms.first { it.id == id }
    }

    override suspend fun updateAlarm(id: String, body: AlarmUpdateDto): AlarmDto {
        checkNetwork()
        updatedAlarms.add(id to body)
        val existing = serverAlarms.first { it.id == id }
        val updated = existing.copy(
            title = body.title ?: existing.title,
            enabled = body.enabled ?: existing.enabled,
            preparationTime = body.preparationTime ?: existing.preparationTime,
            safetyBuffer = body.safetyBuffer ?: existing.safetyBuffer
        )
        val idx = serverAlarms.indexOfFirst { it.id == id }
        serverAlarms[idx] = updated
        return updated
    }

    override suspend fun deleteAlarm(id: String): Response<Unit> {
        checkNetwork()
        deletedAlarmIds.add(id)
        serverAlarms.removeAll { it.id == id }
        return Response.success(Unit)
    }

    override suspend fun enableAlarm(id: String): AlarmDto {
        checkNetwork()
        val existing = serverAlarms.first { it.id == id }
        val updated = existing.copy(enabled = true, status = "scheduled")
        return updated
    }

    override suspend fun disableAlarm(id: String): AlarmDto {
        checkNetwork()
        val existing = serverAlarms.first { it.id == id }
        val updated = existing.copy(enabled = false, status = "disabled")
        return updated
    }

    override suspend fun refreshAlarm(id: String): AlarmDto {
        checkNetwork()
        return serverAlarms.first { it.id == id }
    }

    override suspend fun calculateRoute(body: com.thinkx.ada.network.dto.RouteRequestDto): com.thinkx.ada.network.dto.RouteResultDto {
        checkNetwork()
        return com.thinkx.ada.network.dto.RouteResultDto(
            distanceMeters = 10_000,
            durationSeconds = 600,
            trafficDurationSeconds = 720,
            provider = "google"
        )
    }

    private fun checkNetwork() {
        if (shouldFailWithNetworkError) {
            throw java.net.UnknownHostException("Unable to resolve host api.ada-alarm.app")
        }
        if (shouldFailWithTimeout) {
            throw java.net.SocketTimeoutException("Connection timed out")
        }
    }
}
