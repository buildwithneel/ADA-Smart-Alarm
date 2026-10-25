package com.thinkx.ada.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.data.preferences.UserPreferencesRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class SettingsUiState(
    val defaultPrepMinutes: Int = 30,
    val defaultSafetyBufferMinutes: Int = 10,
    val defaultSnoozeLengthMinutes: Int = 10,
    val isDarkMode: Boolean? = null,
    val vibrationEnabled: Boolean = true,
    val canScheduleExactAlarms: Boolean = true,
    val isLoading: Boolean = true,
    val userMessage: String? = null
)

class SettingsViewModel(
    private val userPreferencesRepository: UserPreferencesRepository,
    private val alarmScheduler: AlarmScheduler
) : ViewModel() {

    private val userMessageFlow = MutableStateFlow<String?>(null)
    private val permissionStateFlow = MutableStateFlow(alarmScheduler.canScheduleExactAlarms())

    val uiState: StateFlow<SettingsUiState> = combine(
        userPreferencesRepository.userPreferencesFlow,
        permissionStateFlow,
        userMessageFlow
    ) { prefs, canSchedule, message ->
        SettingsUiState(
            defaultPrepMinutes = prefs.defaultPreparationMinutes,
            defaultSafetyBufferMinutes = prefs.defaultSafetyBufferMinutes,
            defaultSnoozeLengthMinutes = prefs.defaultSnoozeLengthMinutes,
            isDarkMode = prefs.isDarkMode,
            vibrationEnabled = prefs.vibrationEnabled,
            canScheduleExactAlarms = canSchedule,
            isLoading = false,
            userMessage = message
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = SettingsUiState(
            isLoading = true,
            canScheduleExactAlarms = alarmScheduler.canScheduleExactAlarms()
        )
    )

    fun refreshPermissionState() {
        permissionStateFlow.value = alarmScheduler.canScheduleExactAlarms()
    }

    fun updatePrepMinutes(minutes: Int) {
        val safe = minutes.coerceIn(0, 180)
        val current = uiState.value
        viewModelScope.launch {
            userPreferencesRepository.updateDefaults(
                prepMinutes = safe,
                safetyBufferMinutes = current.defaultSafetyBufferMinutes,
                snoozeMinutes = current.defaultSnoozeLengthMinutes
            )
        }
    }

    fun updateSafetyBufferMinutes(minutes: Int) {
        val safe = minutes.coerceIn(0, 90)
        val current = uiState.value
        viewModelScope.launch {
            userPreferencesRepository.updateDefaults(
                prepMinutes = current.defaultPrepMinutes,
                safetyBufferMinutes = safe,
                snoozeMinutes = current.defaultSnoozeLengthMinutes
            )
        }
    }

    fun updateSnoozeMinutes(minutes: Int) {
        val safe = minutes.coerceIn(1, 60)
        val current = uiState.value
        viewModelScope.launch {
            userPreferencesRepository.updateDefaults(
                prepMinutes = current.defaultPrepMinutes,
                safetyBufferMinutes = current.defaultSafetyBufferMinutes,
                snoozeMinutes = safe
            )
        }
    }

    fun setDarkMode(isDark: Boolean?) {
        viewModelScope.launch {
            userPreferencesRepository.setDarkMode(isDark)
        }
    }

    fun setVibrationEnabled(enabled: Boolean) {
        viewModelScope.launch {
            userPreferencesRepository.setVibrationEnabled(enabled)
        }
    }

    fun clearUserMessage() {
        userMessageFlow.value = null
    }

    class Factory(
        private val userPreferencesRepository: UserPreferencesRepository,
        private val alarmScheduler: AlarmScheduler
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return SettingsViewModel(userPreferencesRepository, alarmScheduler) as T
        }
    }
}
