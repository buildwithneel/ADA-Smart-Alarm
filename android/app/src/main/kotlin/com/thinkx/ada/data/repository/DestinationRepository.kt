package com.thinkx.ada.data.repository

import com.thinkx.ada.data.local.dao.DestinationDao
import com.thinkx.ada.data.local.entity.DestinationEntity
import kotlinx.coroutines.flow.Flow

interface DestinationRepository {
    fun getSavedDestinations(): Flow<List<DestinationEntity>>
    fun getRecentDestinations(limit: Int = 10): Flow<List<DestinationEntity>>
    suspend fun getDestinationById(id: String): DestinationEntity?
    suspend fun saveDestination(destination: DestinationEntity)
    suspend fun updateDestination(destination: DestinationEntity)
    suspend fun deleteDestinationById(id: String)
}

class DestinationRepositoryImpl(
    private val destinationDao: DestinationDao
) : DestinationRepository {

    override fun getSavedDestinations(): Flow<List<DestinationEntity>> =
        destinationDao.getSavedDestinations()

    override fun getRecentDestinations(limit: Int): Flow<List<DestinationEntity>> =
        destinationDao.getRecentDestinations(limit)

    override suspend fun getDestinationById(id: String): DestinationEntity? =
        destinationDao.getDestinationById(id)

    override suspend fun saveDestination(destination: DestinationEntity) =
        destinationDao.insertDestination(destination)

    override suspend fun updateDestination(destination: DestinationEntity) =
        destinationDao.updateDestination(destination)

    override suspend fun deleteDestinationById(id: String) =
        destinationDao.deleteDestinationById(id)
}
