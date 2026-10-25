package com.thinkx.ada.ui.settings

import com.thinkx.ada.alarm.scheduler.FakeAlarmScheduler
import com.thinkx.ada.data.preferences.FakeUserPreferencesRepository
import com.thinkx.ada.data.preferences.UserPreferences
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class SettingsViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var preferencesRepository: FakeUserPreferencesRepository
    private lateinit var scheduler: FakeAlarmScheduler
    private lateinit var viewModel: SettingsViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        preferencesRepository = FakeUserPreferencesRepository(
            UserPreferences(
                defaultPreparationMinutes = 30,
                defaultSafetyBufferMinutes = 10,
                defaultSnoozeLengthMinutes = 10,
                isDarkMode = null,
                vibrationEnabled = true
            )
        )
        scheduler = FakeAlarmScheduler(exactAlarmPermissionGranted = true)
        viewModel = SettingsViewModel(preferencesRepository, scheduler)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `uiState emits initial preferences`() = runTest {
        testDispatcher.scheduler.advanceUntilIdle()
        val state = viewModel.uiState.first { !it.isLoading }

        assertEquals(30, state.defaultPrepMinutes)
        assertEquals(10, state.defaultSafetyBufferMinutes)
        assertEquals(10, state.defaultSnoozeLengthMinutes)
        assertNull(state.isDarkMode)
        assertTrue(state.vibrationEnabled)
        assertTrue(state.canScheduleExactAlarms)
    }

    @Test
    fun `updating preparation minutes modifies preferences`() = runTest {
        viewModel.updatePrepMinutes(45)
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { it.defaultPrepMinutes == 45 }
        assertEquals(45, state.defaultPrepMinutes)
        val prefs = preferencesRepository.userPreferencesFlow.first()
        assertEquals(45, prefs.defaultPreparationMinutes)
    }

    @Test
    fun `updating safety buffer minutes modifies preferences`() = runTest {
        viewModel.updateSafetyBufferMinutes(20)
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { it.defaultSafetyBufferMinutes == 20 }
        assertEquals(20, state.defaultSafetyBufferMinutes)
        val prefs = preferencesRepository.userPreferencesFlow.first()
        assertEquals(20, prefs.defaultSafetyBufferMinutes)
    }

    @Test
    fun `updating snooze minutes modifies preferences`() = runTest {
        viewModel.updateSnoozeMinutes(15)
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { it.defaultSnoozeLengthMinutes == 15 }
        assertEquals(15, state.defaultSnoozeLengthMinutes)
        val prefs = preferencesRepository.userPreferencesFlow.first()
        assertEquals(15, prefs.defaultSnoozeLengthMinutes)
    }

    @Test
    fun `updating theme mode modifies preferences`() = runTest {
        viewModel.setDarkMode(true)
        testDispatcher.scheduler.advanceUntilIdle()

        var state = viewModel.uiState.first { it.isDarkMode == true }
        assertEquals(true, state.isDarkMode)

        viewModel.setDarkMode(false)
        testDispatcher.scheduler.advanceUntilIdle()
        state = viewModel.uiState.first { it.isDarkMode == false }
        assertEquals(false, state.isDarkMode)

        viewModel.setDarkMode(null)
        testDispatcher.scheduler.advanceUntilIdle()
        state = viewModel.uiState.first { it.isDarkMode == null }
        assertNull(state.isDarkMode)
    }

    @Test
    fun `refreshPermissionState reflects changes in exact alarm permission`() = runTest {
        testDispatcher.scheduler.advanceUntilIdle()
        assertTrue(viewModel.uiState.first().canScheduleExactAlarms)

        scheduler.exactAlarmPermissionGranted = false
        viewModel.refreshPermissionState()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { !it.canScheduleExactAlarms }
        assertFalse(state.canScheduleExactAlarms)
    }
}
