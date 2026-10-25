package com.thinkx.ada.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

/**
 * Room Entity representing a saved or recently selected destination.
 */
@Entity(tableName = "destinations")
data class DestinationEntity(
    @PrimaryKey
    val id: String = UUID.randomUUID().toString(),
    val name: String,
    val address: String,
    val latitude: Double,
    val longitude: Double,
    val isSaved: Boolean = true,
    val isRecent: Boolean = false,
    val lastUsedAtEpochMs: Long = System.currentTimeMillis(),
    val createdAtEpochMs: Long = System.currentTimeMillis()
)
