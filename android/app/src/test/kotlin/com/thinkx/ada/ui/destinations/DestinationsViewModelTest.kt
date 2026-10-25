package com.thinkx.ada.ui.destinations

import com.thinkx.ada.data.local.entity.DestinationEntity
import com.thinkx.ada.data.repository.FakeDestinationRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DestinationsViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var repository: FakeDestinationRepository
    private lateinit var viewModel: DestinationsViewModel

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        repository = FakeDestinationRepository()
        viewModel = DestinationsViewModel(repository)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun `uiState emits saved and recent destinations`() = runTest {
        val saved = DestinationEntity(id = "1", name = "Office", address = "Road A", latitude = 22.0, longitude = 72.0, isSaved = true)
        val recent = DestinationEntity(id = "2", name = "Gym", address = "Road B", latitude = 22.1, longitude = 72.1, isRecent = true, isSaved = false)
        repository.saveDestination(saved)
        repository.saveDestination(recent)
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { !it.isLoading }
        assertEquals(1, state.savedDestinations.size)
        assertEquals("Office", state.savedDestinations.first().name)
        assertEquals(1, state.recentDestinations.size)
        assertEquals("Gym", state.recentDestinations.first().name)
    }

    @Test
    fun `add destination creates record and notifies user`() = runTest {
        viewModel.addOrUpdateDestination(
            name = "Charusat",
            address = "Changa Campus",
            lat = 22.599,
            lng = 72.820,
            isSaved = true
        )
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { it.savedDestinations.isNotEmpty() }
        assertEquals(1, state.savedDestinations.size)
        val created = state.savedDestinations.first()
        assertEquals("Charusat", created.name)
        assertEquals("Changa Campus", created.address)
        assertNotNull(state.userMessage)
    }

    @Test
    fun `blank destination name is rejected with user message`() = runTest {
        viewModel.addOrUpdateDestination(
            name = "   ",
            address = "Nowhere",
            isSaved = true
        )
        testDispatcher.scheduler.advanceUntilIdle()

        val state = viewModel.uiState.first { it.userMessage != null }
        assertEquals(0, state.savedDestinations.size)
        assertNotNull(state.userMessage)
        assertTrue(state.userMessage!!.contains("cannot be blank", ignoreCase = true))
    }

    @Test
    fun `update destination updates existing entity`() = runTest {
        val dest = DestinationEntity(id = "dest-1", name = "Old Name", address = "Old Addr", latitude = 0.0, longitude = 0.0, isSaved = true)
        repository.saveDestination(dest)
        testDispatcher.scheduler.advanceUntilIdle()

        viewModel.addOrUpdateDestination(
            id = "dest-1",
            name = "New Name",
            address = "New Addr",
            lat = 23.0,
            lng = 73.0,
            isSaved = true
        )
        testDispatcher.scheduler.advanceUntilIdle()

        val updated = repository.getDestinationById("dest-1")
        assertNotNull(updated)
        assertEquals("New Name", updated?.name)
        assertEquals("New Addr", updated?.address)

        val state = viewModel.uiState.first { it.savedDestinations.any { d -> d.name == "New Name" } }
        assertEquals("New Name", state.savedDestinations.first().name)
    }

    @Test
    fun `delete destination removes record`() = runTest {
        val dest = DestinationEntity(id = "dest-1", name = "To Delete", address = "Addr", latitude = 0.0, longitude = 0.0, isSaved = true)
        repository.saveDestination(dest)
        testDispatcher.scheduler.advanceUntilIdle()

        // Wait until it appears
        viewModel.uiState.first { it.savedDestinations.isNotEmpty() }

        viewModel.deleteDestination("dest-1")
        testDispatcher.scheduler.advanceUntilIdle()

        assertNull(repository.getDestinationById("dest-1"))
        val state = viewModel.uiState.first { it.savedDestinations.isEmpty() }
        assertEquals(0, state.savedDestinations.size)
    }
}
