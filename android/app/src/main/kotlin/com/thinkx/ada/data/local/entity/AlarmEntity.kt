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

    // Synchronization state
    val serverId: String? = null,
    val syncStatus: String = SYNC_STATUS_PENDING,
    val lastSyncedEpochMs: Long? = null,

    // Journey and Dynamic ETA tracking fields
    val scheduledDepartureEpochMs: Long = scheduledAlarmEpochMs,
    val trackingLeadMinutes: Int = 15,
    val approachingThresholdMeters: Int = 1000,
    val arrivalThresholdMeters: Int = 100,
    val originAddress: String? = null,
    val currentEtaEpochMs: Long? = null,
    val lastLocationLat: Double? = null,
    val lastLocationLng: Double? = null,
    val lastLocationEpochMs: Long? = null,
    val remainingDistanceMeters: Int? = null,
    val remainingDurationSeconds: Int? = null,
    val isTrafficAware: Boolean = false,
    val etaSource: String = "FALLBACK",
    val isApproachingAlertSent: Boolean = false,
    val isArrivalConfirmed: Boolean = false,
    val trackingStartedEpochMs: Long? = null,
    val arrivalConfirmedEpochMs: Long? = null,

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

        // Journey Tracking Lifecycle States
        const val STATUS_TRACKING_PENDING = "TRACKING_PENDING"
        const val STATUS_ACTIVE_TRACKING = "ACTIVE_TRACKING"
        const val STATUS_TRACKING_DEGRADED = "TRACKING_DEGRADED"
        const val STATUS_RECALCULATING = "RECALCULATING"
        const val STATUS_APPROACHING = "APPROACHING"
        const val STATUS_ARRIVED = "ARRIVED"
        const val STATUS_STOPPED = "STOPPED"
        const val STATUS_FAILED = "FAILED"

        const val SYNC_STATUS_SYNCED = "SYNCED"
        const val SYNC_STATUS_PENDING = "PENDING"
        const val SYNC_STATUS_PENDING_DELETE = "PENDING_DELETE"
        const val SYNC_STATUS_FAILED = "FAILED"
    }

    val isOneTime: Boolean
        get() = repeatDaysMask == 0

    val trackingStartAttemptEpochMs: Long
        get() = scheduledDepartureEpochMs - (trackingLeadMinutes * 60 * 1000L)
}
