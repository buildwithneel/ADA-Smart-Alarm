package com.thinkx.ada.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.alarm.scheduler.ScheduleResult
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.repository.AlarmRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class HomeUiState(
    val isLoading: Boolean = true,
    val nextAlarm: AlarmEntity? = null,
    val upcomingAlarms: List<AlarmEntity> = emptyList(),
    val canScheduleExactAlarms: Boolean = true,
    val userMessage: String? = null
)

class HomeViewModel(
    private val alarmRepository: AlarmRepository,
    private val alarmScheduler: AlarmScheduler
) : ViewModel() {

    private val userMessageFlow = MutableStateFlow<String?>(null)
    private val permissionStateFlow = MutableStateFlow(alarmScheduler.canScheduleExactAlarms())

    val uiState: StateFlow<HomeUiState> = combine(
        alarmRepository.getAllAlarms(),
        permissionStateFlow,
        userMessageFlow
    ) { alarms, canSchedule, message ->
        val now = System.currentTimeMillis()
        val nextActive = alarms
            .filter { it.isEnabled && it.scheduledAlarmEpochMs >= now }
            .minByOrNull { it.scheduledAlarmEpochMs }

        HomeUiState(
            isLoading = false,
            nextAlarm = nextActive,
            upcomingAlarms = alarms,
            canScheduleExactAlarms = canSchedule,
            userMessage = message
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
            alarmRepository.deleteAlarmById(alarm.id)
            userMessageFlow.value = "Alarm deleted."
        }
    }

    fun clearUserMessage() {
        userMessageFlow.value = null
    }

    class Factory(
        private val alarmRepository: AlarmRepository,
        private val alarmScheduler: AlarmScheduler
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return HomeViewModel(alarmRepository, alarmScheduler) as T
        }
    }
}
