package com.thinkx.ada.data.preferences

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

class FakeUserPreferencesRepository(
    initialPreferences: UserPreferences = UserPreferences()
) : UserPreferencesRepository {

    private val _prefs = MutableStateFlow(initialPreferences)
    override val userPreferencesFlow: Flow<UserPreferences> = _prefs.asStateFlow()

    override suspend fun updateDefaults(prepMinutes: Int, safetyBufferMinutes: Int, snoozeMinutes: Int) {
        _prefs.value = _prefs.value.copy(
            defaultPreparationMinutes = prepMinutes,
            defaultSafetyBufferMinutes = safetyBufferMinutes,
            defaultSnoozeLengthMinutes = snoozeMinutes
        )
    }

    override suspend fun setOnboardingCompleted(completed: Boolean) {
        _prefs.value = _prefs.value.copy(hasCompletedOnboarding = completed)
    }

    override suspend fun setVibrationEnabled(enabled: Boolean) {
        _prefs.value = _prefs.value.copy(vibrationEnabled = enabled)
    }

    override suspend fun setDarkMode(isDark: Boolean?) {
        _prefs.value = _prefs.value.copy(isDarkMode = isDark)
    }
}
