package com.thinkx.ada.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.thinkx.ada.data.local.entity.DestinationEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface DestinationDao {

    @Query("SELECT * FROM destinations WHERE isSaved = 1 ORDER BY name ASC")
    fun getSavedDestinations(): Flow<List<DestinationEntity>>

    @Query("SELECT * FROM destinations WHERE isRecent = 1 ORDER BY lastUsedAtEpochMs DESC LIMIT :limit")
    fun getRecentDestinations(limit: Int = 10): Flow<List<DestinationEntity>>

    @Query("SELECT * FROM destinations WHERE id = :id LIMIT 1")
    suspend fun getDestinationById(id: String): DestinationEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDestination(destination: DestinationEntity)

    @Update
    suspend fun updateDestination(destination: DestinationEntity)

    @Delete
    suspend fun deleteDestination(destination: DestinationEntity)

    @Query("DELETE FROM destinations WHERE id = :id")
    suspend fun deleteDestinationById(id: String)
}
