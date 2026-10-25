package com.thinkx.ada.ui.alarm

import com.thinkx.ada.alarm.scheduler.FakeAlarmScheduler
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.local.entity.DestinationEntity
import com.thinkx.ada.data.preferences.FakeUserPreferencesRepository
import com.thinkx.ada.data.preferences.UserPreferences
import com.thinkx.ada.data.repository.FakeAlarmRepository
import com.thinkx.ada.data.repository.FakeDestinationRepository
import com.thinkx.ada.domain.engine.AdaCalculationEngine
import com.thinkx.ada.domain.model.CalculationInput
import com.thinkx.ada.util.DateTimeUtils
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
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime

@OptIn(ExperimentalCoroutinesApi::class)
class CreateEditAlarmViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var alarmRepository: FakeAlarmRepository
    private lateinit var destinationRepository: FakeDestinationRepository
    private lateinit var preferencesRepository: FakeUserPreferencesRepository
    private lateinit var alarmScheduler: FakeAlarmScheduler

    private val baseNowEpochMs = 1700000000000L

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        alarmRepository = FakeAlarmRepository()
        destinationRepository = FakeDestinationRepository()
        preferencesRepository = FakeUserPreferencesRepository(
            UserPreferences(
                defaultPreparationMinutes = 30,
                defaultSafetyBufferMinutes = 10
            )
        )
        alarmScheduler = FakeAlarmScheduler(
            exactAlarmPermissionGranted = true,
            mockCurrentTimeEpochMs = baseNowEpochMs
        )
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun createViewModel(alarmId: String? = null): CreateEditAlarmViewModel {
        return CreateEditAlarmViewModel(
            alarmId = alarmId,
            alarmRepository = alarmRepository,
            destinationRepository = destinationRepository,
            userPreferencesRepository = preferencesRepository,
            alarmScheduler = alarmScheduler
        )
    }

    @Test
    fun `create mode loads defaults from user preferences and calculates schedule`() = runTest {
        val viewModel = createViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertFalse(state.isEditMode)
        assertEquals(30, state.preparationDurationMinutes)
        assertEquals(10, state.safetyBufferMinutes)
        assertNotNull(state.calculationResult)

        // Verify calculation preview consistency with AdaCalculationEngine
        val targetDateTime = LocalDateTime.of(state.selectedDate, state.selectedTime)
        val expected = AdaCalculationEngine.calculate(
            CalculationInput(
                requiredArrival = targetDateTime,
                travelDurationMinutes = state.travelDurationMinutes,
                preparationDurationMinutes = state.preparationDurationMinutes,
                safetyBufferMinutes = state.safetyBufferMinutes
            )
        )
        assertEquals(expected.recommendedWakeTime, state.calculationResult?.recommendedWakeTime)
        assertEquals(expected.recommendedLeaveTime, state.calculationResult?.recommendedLeaveTime)
        assertEquals(expected.plannedArrival, state.calculationResult?.plannedArrival)
    }

    @Test
    fun `edit mode pre-fills existing alarm attributes`() = runTest {
        val futureEpochMs = System.currentTimeMillis() + 86400000L
        val existingAlarm = AlarmEntity(
            id = "alarm-edit-1",
            title = "Campus Lecture",
            destinationName = "Charusat University",
            destinationAddress = "Changa, Gujarat",
            destinationLat = 22.599,
            destinationLng = 72.820,
            requiredArrivalEpochMs = futureEpochMs,
            plannedArrivalEpochMs = futureEpochMs - 600000L,
            recommendedLeaveEpochMs = futureEpochMs - 2700000L,
            recommendedWakeEpochMs = futureEpochMs - 4500000L,
            scheduledAlarmEpochMs = futureEpochMs - 4500000L,
            travelDurationMinutes = 35,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            isEnabled = true
        )
        alarmRepository.saveAlarm(existingAlarm)

        val viewModel = createViewModel(alarmId = existingAlarm.id)
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertTrue(state.isEditMode)
        assertEquals("Charusat University", state.destinationName)
        assertEquals("Campus Lecture", state.title)
        assertEquals(35, state.travelDurationMinutes)
        assertEquals(30, state.preparationDurationMinutes)
        assertEquals(10, state.safetyBufferMinutes)
    }

    @Test
    fun `saving with blank destination triggers validation error and does not save`() = runTest {
        val viewModel = createViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.onDestinationChange("")
        viewModel.saveAlarm()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertNotNull(state.validationError)
        assertFalse(state.isSaveSuccess)
        assertEquals(0, alarmRepository.alarms.size)
    }

    @Test
    fun `saving with past arrival time triggers validation error and prevents saving`() = runTest {
        val viewModel = createViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.onDestinationChange("Office")
        // Set date to yesterday
        viewModel.onDateChange(LocalDate.now().minusDays(1))
        viewModel.saveAlarm()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertNotNull(state.validationError)
        assertTrue(state.isDeadlinePast || state.isWakeTimePast)
        assertFalse(state.isSaveSuccess)
        assertEquals(0, alarmRepository.alarms.size)
    }

    @Test
    fun `creating and saving alarm schedules in AlarmScheduler and persists in Room`() = runTest {
        val viewModel = createViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.onDestinationChange("Tech Park", "Building B")
        viewModel.onTitleChange("Morning Sync")
        viewModel.onDateChange(LocalDate.now().plusDays(2))
        viewModel.onTimeChange(LocalTime.of(9, 30))
        viewModel.onTravelDurationChange(40)
        viewModel.onPreparationDurationChange(25)
        viewModel.onSafetyBufferChange(15)

        viewModel.saveAlarm()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertTrue(state.isSaveSuccess)
        assertNull(state.validationError)

        assertEquals(1, alarmRepository.alarms.size)
        val saved = alarmRepository.alarms.values.first()
        assertEquals("Morning Sync", saved.title)
        assertEquals("Tech Park", saved.destinationName)
        assertEquals(40, saved.travelDurationMinutes)
        assertEquals(25, saved.preparationDurationMinutes)
        assertEquals(15, saved.safetyBufferMinutes)
        assertTrue(saved.isEnabled)

        // Native scheduler was invoked
        assertTrue(alarmScheduler.scheduledAlarms.containsKey(saved.id))
        assertEquals(saved.scheduledAlarmEpochMs, alarmScheduler.scheduledAlarms[saved.id]?.scheduledAlarmEpochMs)
    }

    @Test
    fun `editing alarm replaces scheduled time and updates Room database`() = runTest {
        val initialFutureMs = System.currentTimeMillis() + 86400000L
        val originalAlarm = AlarmEntity(
            id = "alarm-to-edit",
            title = "Trip",
            destinationName = "Airport",
            destinationAddress = "Terminal 2",
            destinationLat = 22.0,
            destinationLng = 72.0,
            requiredArrivalEpochMs = initialFutureMs,
            plannedArrivalEpochMs = initialFutureMs - 600000L,
            recommendedLeaveEpochMs = initialFutureMs - 3000000L,
            recommendedWakeEpochMs = initialFutureMs - 4800000L,
            scheduledAlarmEpochMs = initialFutureMs - 4800000L,
            travelDurationMinutes = 40,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            isEnabled = true
        )
        alarmRepository.saveAlarm(originalAlarm)
        alarmScheduler.schedule(originalAlarm)

        val viewModel = createViewModel(alarmId = originalAlarm.id)
        testDispatcher.scheduler.advanceUntilIdle()

        // Change destination and travel duration
        viewModel.onDestinationChange("International Airport")
        viewModel.onTravelDurationChange(50)
        viewModel.saveAlarm()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertTrue(state.isSaveSuccess)

        val updated = alarmRepository.getAlarmById("alarm-to-edit")
        assertNotNull(updated)
        assertEquals("International Airport", updated?.destinationName)
        assertEquals(50, updated?.travelDurationMinutes)

        // Scheduler contains updated schedule
        val scheduled = alarmScheduler.scheduledAlarms["alarm-to-edit"]
        assertNotNull(scheduled)
        assertEquals(updated?.scheduledAlarmEpochMs, scheduled?.scheduledAlarmEpochMs)
    }

    @Test
    fun `saving alarm when exact alarm permission is missing does not silently schedule as active`() = runTest {
        alarmScheduler.exactAlarmPermissionGranted = false

        val viewModel = createViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.onDestinationChange("Office")
        viewModel.onDateChange(LocalDate.now().plusDays(2))
        viewModel.onTimeChange(LocalTime.of(10, 0))

        viewModel.saveAlarm()
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first()
        assertTrue(state.permissionDenied)
        assertFalse(alarmScheduler.scheduledAlarms.containsKey(state.alarmId ?: ""))

        // If saved, it is saved as disabled
        val saved = alarmRepository.alarms.values.firstOrNull()
        if (saved != null) {
            assertFalse(saved.isEnabled)
            assertEquals(AlarmEntity.STATUS_CANCELLED, saved.status)
        }
    }

    @Test
    fun `quick destination selection populates fields from saved destinations`() = runTest {
        val dest = DestinationEntity(
            id = "saved-1",
            name = "Charusat Changa",
            address = "Anand, Gujarat",
            latitude = 22.599,
            longitude = 72.820,
            isSaved = true
        )
        destinationRepository.saveDestination(dest)

        val viewModel = createViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.selectDestination(dest)
        val state = viewModel.uiState.first()
        assertEquals("Charusat Changa", state.destinationName)
        assertEquals("Anand, Gujarat", state.destinationAddress)
        assertEquals(22.599, state.destinationLat, 0.001)
    }
}
