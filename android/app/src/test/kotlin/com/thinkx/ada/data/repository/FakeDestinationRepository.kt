package com.thinkx.ada.data.repository

import com.thinkx.ada.data.local.entity.DestinationEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.map

class FakeDestinationRepository : DestinationRepository {

    val destinations = MutableStateFlow<Map<String, DestinationEntity>>(emptyMap())

    override fun getSavedDestinations(): Flow<List<DestinationEntity>> {
        return destinations.map { map ->
            map.values.filter { it.isSaved }.sortedBy { it.name }
        }
    }

    override fun getRecentDestinations(limit: Int): Flow<List<DestinationEntity>> {
        return destinations.map { map ->
            map.values.filter { it.isRecent }
                .sortedByDescending { it.lastUsedAtEpochMs }
                .take(limit)
        }
    }

    override suspend fun getDestinationById(id: String): DestinationEntity? {
        return destinations.value[id]
    }

    override suspend fun saveDestination(destination: DestinationEntity) {
        val current = destinations.value.toMutableMap()
        current[destination.id] = destination
        destinations.value = current
    }

    override suspend fun updateDestination(destination: DestinationEntity) {
        saveDestination(destination)
    }

    override suspend fun deleteDestinationById(id: String) {
        val current = destinations.value.toMutableMap()
        current.remove(id)
        destinations.value = current
    }
}
