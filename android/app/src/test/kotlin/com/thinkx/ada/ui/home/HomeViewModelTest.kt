package com.thinkx.ada.ui.home

import com.thinkx.ada.alarm.scheduler.FakeAlarmScheduler
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.repository.FakeAlarmRepository
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

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var alarmRepository: FakeAlarmRepository
    private lateinit var alarmScheduler: FakeAlarmScheduler
    private lateinit var viewModel: HomeViewModel

    private val baseNowEpochMs get() = System.currentTimeMillis()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        alarmRepository = FakeAlarmRepository()
        alarmScheduler = FakeAlarmScheduler(
            exactAlarmPermissionGranted = true,
            mockCurrentTimeEpochMs = baseNowEpochMs
        )
        viewModel = HomeViewModel(alarmRepository, alarmScheduler)
    }


    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun createAlarm(
        id: String = "alarm-1",
        scheduledTime: Long = baseNowEpochMs + 3600000L,
        isEnabled: Boolean = true
    ): AlarmEntity {
        return AlarmEntity(
            id = id,
            title = "Office Commute",
            destinationName = "Work Office",
            destinationAddress = "Station Road",
            destinationLat = 22.5,
            destinationLng = 72.8,
            requiredArrivalEpochMs = scheduledTime + 3600000L,
            plannedArrivalEpochMs = scheduledTime + 3000000L,
            recommendedLeaveEpochMs = scheduledTime + 1800000L,
            recommendedWakeEpochMs = scheduledTime,
            scheduledAlarmEpochMs = scheduledTime,
            travelDurationMinutes = 20,
            preparationDurationMinutes = 30,
            safetyBufferMinutes = 10,
            isEnabled = isEnabled
        )
    }

    @Test
    fun `uiState initially loads and updates when alarms exist`() = runTest {
        val alarm = createAlarm()
        alarmRepository.saveAlarm(alarm)
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { !it.isLoading }
        assertEquals(1, state.upcomingAlarms.size)
        assertNotNull(state.nextAlarm)
        assertEquals("alarm-1", state.nextAlarm?.id)
        assertTrue(state.canScheduleExactAlarms)
    }

    @Test
    fun `toggling alarm on schedules with scheduler and updates database`() = runTest {
        val alarm = createAlarm(isEnabled = false)
        alarmRepository.saveAlarm(alarm)
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.toggleAlarm(alarm, isEnabled = true)
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(alarmScheduler.scheduledAlarms.containsKey(alarm.id))
        val updated = alarmRepository.getAlarmById(alarm.id)
        assertNotNull(updated)
        assertTrue(updated!!.isEnabled)
        assertEquals(AlarmEntity.STATUS_SCHEDULED, updated.status)
    }

    @Test
    fun `toggling alarm off cancels in scheduler and updates database`() = runTest {
        val alarm = createAlarm(isEnabled = true)
        alarmRepository.saveAlarm(alarm)
        alarmScheduler.schedule(alarm)
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.toggleAlarm(alarm, isEnabled = false)
        testDispatcher.scheduler.advanceUntilIdle()

        assertFalse(alarmScheduler.scheduledAlarms.containsKey(alarm.id))
        assertTrue(alarmScheduler.cancelledAlarmIds.contains(alarm.id))
        val updated = alarmRepository.getAlarmById(alarm.id)
        assertNotNull(updated)
        assertFalse(updated!!.isEnabled)
        assertEquals(AlarmEntity.STATUS_CANCELLED, updated.status)
    }

    @Test
    fun `enabling alarm without exact alarm permission fails and leaves alarm disabled`() = runTest {
        alarmScheduler.exactAlarmPermissionGranted = false
        val alarm = createAlarm(isEnabled = false)
        alarmRepository.saveAlarm(alarm)
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.toggleAlarm(alarm, isEnabled = true)
        testDispatcher.scheduler.advanceUntilIdle()

        assertFalse(alarmScheduler.scheduledAlarms.containsKey(alarm.id))
        val updated = alarmRepository.getAlarmById(alarm.id)
        assertFalse(updated!!.isEnabled)
        val state = viewModel.uiState.first { it.userMessage != null }
        assertNotNull(state.userMessage)
    }

    @Test
    fun `enabling past alarm fails and rejects past schedule`() = runTest {
        val pastAlarm = createAlarm(scheduledTime = baseNowEpochMs - 60000L, isEnabled = false)
        alarmRepository.saveAlarm(pastAlarm)
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.toggleAlarm(pastAlarm, isEnabled = true)
        testDispatcher.scheduler.advanceUntilIdle()

        assertFalse(alarmScheduler.scheduledAlarms.containsKey(pastAlarm.id))
        val updated = alarmRepository.getAlarmById(pastAlarm.id)
        assertFalse(updated!!.isEnabled)
        val state = viewModel.uiState.first { it.userMessage != null }
        assertNotNull(state.userMessage)
        val msg = state.userMessage ?: ""
        assertTrue(msg.contains("passed", ignoreCase = true) || msg.contains("past", ignoreCase = true))
    }

    @Test
    fun `deleting alarm cancels native scheduler and removes from database`() = runTest {
        val alarm = createAlarm(isEnabled = true)
        alarmRepository.saveAlarm(alarm)
        alarmScheduler.schedule(alarm)
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.deleteAlarm(alarm)
        testDispatcher.scheduler.advanceUntilIdle()

        assertFalse(alarmScheduler.scheduledAlarms.containsKey(alarm.id))
        assertTrue(alarmScheduler.cancelledAlarmIds.contains(alarm.id))
        assertNull(alarmRepository.getAlarmById(alarm.id))
    }

    @Test
    fun `toggleAlarm and deleteAlarm synchronize journeyScheduler tracking start and cancellation`() = runTest {
        val fakeJourneyScheduler = FakeJourneyScheduler()
        val customViewModel = HomeViewModel(
            alarmRepository = alarmRepository,
            alarmScheduler = alarmScheduler,
            journeyScheduler = fakeJourneyScheduler
        )

        val alarm = createAlarm(id = "journey-test-1", isEnabled = false)
        alarmRepository.saveAlarm(alarm)
        testDispatcher.scheduler.advanceUntilIdle()

        // 1. Toggle ON -> should schedule tracking start
        customViewModel.toggleAlarm(alarm, isEnabled = true)
        testDispatcher.scheduler.advanceUntilIdle()
        assertTrue("Journey tracking must be scheduled when alarm enabled", fakeJourneyScheduler.scheduledJourneys.containsKey("journey-test-1"))

        // 2. Toggle OFF -> should cancel tracking start
        val enabledAlarm = alarmRepository.getAlarmById("journey-test-1")!!
        customViewModel.toggleAlarm(enabledAlarm, isEnabled = false)
        testDispatcher.scheduler.advanceUntilIdle()
        assertTrue("Journey tracking must be cancelled when alarm disabled", fakeJourneyScheduler.cancelledJourneyIds.contains("journey-test-1"))

        // 3. Delete -> should cancel tracking start
        customViewModel.deleteAlarm(enabledAlarm)
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals(2, fakeJourneyScheduler.cancelledJourneyIds.count { it == "journey-test-1" })
    }
}

private class FakeJourneyScheduler : com.thinkx.ada.journey.scheduler.JourneyScheduler {
    val scheduledJourneys = mutableMapOf<String, AlarmEntity>()
    val cancelledJourneyIds = mutableListOf<String>()

    override fun scheduleTrackingStart(journey: AlarmEntity): Boolean {
        scheduledJourneys[journey.id] = journey
        return true
    }

    override fun cancelTrackingStart(journeyId: String) {
        scheduledJourneys.remove(journeyId)
        cancelledJourneyIds.add(journeyId)
    }

    override fun canScheduleExactAlarms(): Boolean = true
}
