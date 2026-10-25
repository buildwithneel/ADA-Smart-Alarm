package com.thinkx.ada.data.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException

val Context.adaPreferencesDataStore: DataStore<Preferences> by preferencesDataStore(name = "ada_user_preferences")

data class UserPreferences(
    val defaultPreparationMinutes: Int = 30,
    val defaultSafetyBufferMinutes: Int = 10,
    val defaultSnoozeLengthMinutes: Int = 10,
    val defaultTransportMode: String = "DRIVING",
    val vibrationEnabled: Boolean = true,
    val defaultSoundUri: String? = null,
    val isDarkMode: Boolean? = null, // null means follow system
    val hasCompletedOnboarding: Boolean = false
)

interface UserPreferencesRepository {
    val userPreferencesFlow: Flow<UserPreferences>
    suspend fun updateDefaults(prepMinutes: Int, safetyBufferMinutes: Int, snoozeMinutes: Int)
    suspend fun setOnboardingCompleted(completed: Boolean)
    suspend fun setVibrationEnabled(enabled: Boolean)
    suspend fun setDarkMode(isDark: Boolean?)

    companion object {
        operator fun invoke(context: Context): UserPreferencesRepository =
            UserPreferencesRepositoryImpl(context)
    }
}

class UserPreferencesRepositoryImpl(private val context: Context) : UserPreferencesRepository {

    private val dataStore = context.adaPreferencesDataStore

    private object PreferencesKeys {
        val DEFAULT_PREP_MINUTES = intPreferencesKey("default_prep_minutes")
        val DEFAULT_SAFETY_BUFFER_MINUTES = intPreferencesKey("default_safety_buffer_minutes")
        val DEFAULT_SNOOZE_LENGTH_MINUTES = intPreferencesKey("default_snooze_length_minutes")
        val DEFAULT_TRANSPORT_MODE = stringPreferencesKey("default_transport_mode")
        val VIBRATION_ENABLED = booleanPreferencesKey("vibration_enabled")
        val DEFAULT_SOUND_URI = stringPreferencesKey("default_sound_uri")
        val IS_DARK_MODE = booleanPreferencesKey("is_dark_mode")
        val HAS_COMPLETED_ONBOARDING = booleanPreferencesKey("has_completed_onboarding")
    }

    override val userPreferencesFlow: Flow<UserPreferences> = dataStore.data
        .catch { exception ->
            if (exception is IOException) {
                emit(emptyPreferences())
            } else {
                throw exception
            }
        }
        .map { preferences ->
            UserPreferences(
                defaultPreparationMinutes = preferences[PreferencesKeys.DEFAULT_PREP_MINUTES] ?: 30,
                defaultSafetyBufferMinutes = preferences[PreferencesKeys.DEFAULT_SAFETY_BUFFER_MINUTES] ?: 10,
                defaultSnoozeLengthMinutes = preferences[PreferencesKeys.DEFAULT_SNOOZE_LENGTH_MINUTES] ?: 10,
                defaultTransportMode = preferences[PreferencesKeys.DEFAULT_TRANSPORT_MODE] ?: "DRIVING",
                vibrationEnabled = preferences[PreferencesKeys.VIBRATION_ENABLED] ?: true,
                defaultSoundUri = preferences[PreferencesKeys.DEFAULT_SOUND_URI],
                isDarkMode = preferences[PreferencesKeys.IS_DARK_MODE],
                hasCompletedOnboarding = preferences[PreferencesKeys.HAS_COMPLETED_ONBOARDING] ?: false
            )
        }

    override suspend fun updateDefaults(prepMinutes: Int, safetyBufferMinutes: Int, snoozeMinutes: Int) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.DEFAULT_PREP_MINUTES] = prepMinutes
            preferences[PreferencesKeys.DEFAULT_SAFETY_BUFFER_MINUTES] = safetyBufferMinutes
            preferences[PreferencesKeys.DEFAULT_SNOOZE_LENGTH_MINUTES] = snoozeMinutes
        }
    }

    override suspend fun setOnboardingCompleted(completed: Boolean) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.HAS_COMPLETED_ONBOARDING] = completed
        }
    }

    override suspend fun setVibrationEnabled(enabled: Boolean) {
        dataStore.edit { preferences ->
            preferences[PreferencesKeys.VIBRATION_ENABLED] = enabled
        }
    }

    override suspend fun setDarkMode(isDark: Boolean?) {
        dataStore.edit { preferences ->
            if (isDark == null) {
                preferences.remove(PreferencesKeys.IS_DARK_MODE)
            } else {
                preferences[PreferencesKeys.IS_DARK_MODE] = isDark
            }
        }
    }
}
