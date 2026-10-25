package com.thinkx.ada.ui.destinations

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.thinkx.ada.data.local.entity.DestinationEntity
import com.thinkx.ada.data.repository.DestinationRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.UUID

data class DestinationsUiState(
    val savedDestinations: List<DestinationEntity> = emptyList(),
    val recentDestinations: List<DestinationEntity> = emptyList(),
    val isLoading: Boolean = true,
    val userMessage: String? = null
)

class DestinationsViewModel(
    private val destinationRepository: DestinationRepository
) : ViewModel() {

    private val userMessageFlow = MutableStateFlow<String?>(null)

    val uiState: StateFlow<DestinationsUiState> = combine(
        destinationRepository.getSavedDestinations(),
        destinationRepository.getRecentDestinations(10),
        userMessageFlow
    ) { saved, recent, message ->
        DestinationsUiState(
            savedDestinations = saved,
            recentDestinations = recent,
            isLoading = false,
            userMessage = message
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = DestinationsUiState(isLoading = true)
    )

    fun addOrUpdateDestination(
        id: String? = null,
        name: String,
        address: String,
        lat: Double = 0.0,
        lng: Double = 0.0,
        isSaved: Boolean = true
    ) {
        if (name.isBlank()) {
            userMessageFlow.value = "Destination name cannot be blank."
            return
        }

        viewModelScope.launch {
            val destination = DestinationEntity(
                id = id ?: UUID.randomUUID().toString(),
                name = name.trim(),
                address = address.trim(),
                latitude = lat,
                longitude = lng,
                isSaved = isSaved,
                lastUsedAtEpochMs = System.currentTimeMillis()
            )
            destinationRepository.saveDestination(destination)
            userMessageFlow.value = if (id == null) "Destination saved." else "Destination updated."
        }
    }

    fun deleteDestination(id: String) {
        viewModelScope.launch {
            destinationRepository.deleteDestinationById(id)
            userMessageFlow.value = "Destination deleted."
        }
    }

    fun clearUserMessage() {
        userMessageFlow.value = null
    }

    class Factory(
        private val destinationRepository: DestinationRepository
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return DestinationsViewModel(destinationRepository) as T
        }
    }
}
