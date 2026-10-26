package com.thinkx.ada.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.alarm.scheduler.ScheduleResult
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.repository.AlarmRepository
import com.thinkx.ada.data.sync.AlarmSyncRepository
import com.thinkx.ada.data.sync.SyncState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class HomeUiState(
    val isLoading: Boolean = true,
    val activeJourney: AlarmEntity? = null,
    val nextAlarm: AlarmEntity? = null,
    val upcomingAlarms: List<AlarmEntity> = emptyList(),
    val canScheduleExactAlarms: Boolean = true,
    val userMessage: String? = null,
    val syncState: SyncState = SyncState.Idle
)

class HomeViewModel(
    private val alarmRepository: AlarmRepository,
    private val alarmScheduler: AlarmScheduler,
    private val syncRepository: AlarmSyncRepository? = null
) : ViewModel() {

    private val userMessageFlow = MutableStateFlow<String?>(null)
    private val permissionStateFlow = MutableStateFlow(alarmScheduler.canScheduleExactAlarms())

    val uiState: StateFlow<HomeUiState> = combine(
        alarmRepository.getAllAlarms(),
        permissionStateFlow,
        userMessageFlow,
        syncRepository?.syncStateFlow ?: MutableStateFlow(SyncState.Idle)
    ) { alarms, canSchedule, message, syncState ->
        val now = System.currentTimeMillis()
        val active = alarms.firstOrNull {
            it.isEnabled && it.status in setOf(
                AlarmEntity.STATUS_ACTIVE_TRACKING,
                AlarmEntity.STATUS_TRACKING_DEGRADED,
                AlarmEntity.STATUS_RECALCULATING,
                AlarmEntity.STATUS_APPROACHING
            )
        }
        val nextActive = active ?: alarms
            .filter { it.isEnabled && it.scheduledDepartureEpochMs >= now }
            .minByOrNull { it.scheduledDepartureEpochMs }
            ?: alarms
                .filter { it.isEnabled && it.scheduledAlarmEpochMs >= now }
                .minByOrNull { it.scheduledAlarmEpochMs }

        HomeUiState(
            isLoading = false,
            activeJourney = active,
            nextAlarm = nextActive,
            upcomingAlarms = alarms,
            canScheduleExactAlarms = canSchedule,
            userMessage = message,
            syncState = syncState
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = HomeUiState(
            isLoading = true,
            canScheduleExactAlarms = alarmScheduler.canScheduleExactAlarms()
        )
    )

    fun refreshPermissionState() {
        permissionStateFlow.value = alarmScheduler.canScheduleExactAlarms()
    }

    fun syncNow() {
        viewModelScope.launch {
            syncRepository?.syncAlarms()
        }
    }

    fun toggleAlarm(alarm: AlarmEntity, isEnabled: Boolean) {
        viewModelScope.launch {
            if (isEnabled) {
                if (!alarmScheduler.canScheduleExactAlarms()) {
                    userMessageFlow.value = "Exact alarm permission is required to enable alarms."
                    refreshPermissionState()
                    return@launch
                }

                val now = System.currentTimeMillis()
                if (alarm.scheduledAlarmEpochMs <= now) {
                    userMessageFlow.value = "Cannot enable alarm: wake time has already passed. Please edit the arrival time."
                    return@launch
                }

                // Update database
                alarmRepository.setAlarmEnabled(alarm.id, true)
                alarmRepository.setAlarmStatus(alarm.id, AlarmEntity.STATUS_SCHEDULED)

                // Synchronize with native scheduler
                when (val result = alarmScheduler.schedule(alarm.copy(isEnabled = true, status = AlarmEntity.STATUS_SCHEDULED))) {
                    is ScheduleResult.Success -> {
                        // Successfully scheduled
                    }
                    is ScheduleResult.PermissionDenied -> {
                        alarmRepository.setAlarmEnabled(alarm.id, false)
                        userMessageFlow.value = "Exact alarm permission denied."
                        refreshPermissionState()
                    }
                    is ScheduleResult.PastTime -> {
                        alarmRepository.setAlarmEnabled(alarm.id, false)
                        userMessageFlow.value = "Cannot schedule alarm in the past."
                    }
                    is ScheduleResult.Error -> {
                        alarmRepository.setAlarmEnabled(alarm.id, false)
                        userMessageFlow.value = "Scheduling error: ${result.message}"
                    }
                }
            } else {
                alarmScheduler.cancel(alarm.id)
                alarmRepository.setAlarmEnabled(alarm.id, false)
                alarmRepository.setAlarmStatus(alarm.id, AlarmEntity.STATUS_CANCELLED)
            }
        }
    }

    fun deleteAlarm(alarm: AlarmEntity) {
        viewModelScope.launch {
            alarmScheduler.cancel(alarm.id)
            if (syncRepository != null) {
                syncRepository.deleteRemoteAlarm(alarm.id)
            } else {
                alarmRepository.deleteAlarmById(alarm.id)
            }
            userMessageFlow.value = "Alarm deleted."
        }
    }

    fun startTracking(journey: AlarmEntity, context: android.content.Context) {
        val fineLocationGranted = androidx.core.content.ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        val coarseLocationGranted = androidx.core.content.ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.ACCESS_COARSE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

        if (!fineLocationGranted && !coarseLocationGranted) {
            userMessageFlow.value = "Location permission is required for live journey tracking."
            return
        }

        val serviceIntent = android.content.Intent(context, com.thinkx.ada.journey.service.JourneyTrackingService::class.java).apply {
            action = com.thinkx.ada.journey.service.JourneyTrackingService.ACTION_START_TRACKING
            putExtra(com.thinkx.ada.journey.service.JourneyTrackingService.EXTRA_JOURNEY_ID, journey.id)
            putExtra(com.thinkx.ada.journey.service.JourneyTrackingService.EXTRA_JOURNEY_TITLE, journey.title)
            putExtra(com.thinkx.ada.journey.service.JourneyTrackingService.EXTRA_DESTINATION_NAME, journey.destinationName)
            putExtra(com.thinkx.ada.journey.service.JourneyTrackingService.EXTRA_DESTINATION_LAT, journey.destinationLat)
            putExtra(com.thinkx.ada.journey.service.JourneyTrackingService.EXTRA_DESTINATION_LNG, journey.destinationLng)
            putExtra(com.thinkx.ada.journey.service.JourneyTrackingService.EXTRA_APPROACHING_THRESHOLD_METERS, journey.approachingThresholdMeters)
            putExtra(com.thinkx.ada.journey.service.JourneyTrackingService.EXTRA_ARRIVAL_THRESHOLD_METERS, journey.arrivalThresholdMeters)
        }
        androidx.core.content.ContextCompat.startForegroundService(context, serviceIntent)
        userMessageFlow.value = "Live journey tracking started."
    }

    fun stopTracking(context: android.content.Context) {
        val serviceIntent = android.content.Intent(context, com.thinkx.ada.journey.service.JourneyTrackingService::class.java).apply {
            action = com.thinkx.ada.journey.service.JourneyTrackingService.ACTION_STOP_TRACKING
        }
        context.startService(serviceIntent)
        userMessageFlow.value = "Live tracking stopped."
    }

    fun clearUserMessage() {
        userMessageFlow.value = null
    }

    class Factory(
        private val alarmRepository: AlarmRepository,
        private val alarmScheduler: AlarmScheduler,
        private val syncRepository: AlarmSyncRepository? = null
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return HomeViewModel(alarmRepository, alarmScheduler, syncRepository) as T
        }
    }
}
