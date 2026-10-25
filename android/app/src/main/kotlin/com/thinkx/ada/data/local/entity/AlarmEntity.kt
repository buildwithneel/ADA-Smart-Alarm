package com.thinkx.ada.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

/**
 * Room Entity representing a Smart Alarm persisted locally on the Android device.
 *
 * All timestamps are stored as canonical epoch milliseconds in UTC to ensure
 * correct handling of time zones, DST shifts, and date boundaries without
 * relying on display string formats.
 */
@Entity(tableName = "alarms")
data class AlarmEntity(
    @PrimaryKey
    val id: String = UUID.randomUUID().toString(),
    val title: String,
    val destinationId: String? = null,
    val destinationName: String,
    val destinationAddress: String,
    val destinationLat: Double,
    val destinationLng: Double,
    val originLat: Double? = null,
    val originLng: Double? = null,

    // Canonical time milestones stored as Epoch Milliseconds
    val requiredArrivalEpochMs: Long,
    val plannedArrivalEpochMs: Long,
    val recommendedLeaveEpochMs: Long,
    val recommendedWakeEpochMs: Long,
    val scheduledAlarmEpochMs: Long,

    // Durations in minutes
    val travelDurationMinutes: Int,
    val preparationDurationMinutes: Int,
    val safetyBufferMinutes: Int,
    val trafficDelayMinutes: Int = 0,
    val weatherBufferMinutes: Int = 0,

    val transportMode: String = "DRIVING",
    val isEnabled: Boolean = true,
    val isSnoozed: Boolean = false,
    val snoozeCount: Int = 0,
    val snoozeLengthMinutes: Int = 10,
    val status: String = STATUS_SCHEDULED,
    val repeatDaysMask: Int = 0, // Bitmask: 0 = one-time; 1=Mon, 2=Tue, 4=Wed, etc.
    val soundUri: String? = null,
    val vibrationEnabled: Boolean = true,

    val lastCalculatedEpochMs: Long = System.currentTimeMillis(),
    val createdAtEpochMs: Long = System.currentTimeMillis(),
    val updatedAtEpochMs: Long = System.currentTimeMillis()
) {
    companion object {
        const val STATUS_SCHEDULED = "SCHEDULED"
        const val STATUS_RINGING = "RINGING"
        const val STATUS_DISMISSED = "DISMISSED"
        const val STATUS_SNOOZED = "SNOOZED"
        const val STATUS_CANCELLED = "CANCELLED"
    }

    val isOneTime: Boolean
        get() = repeatDaysMask == 0
}
