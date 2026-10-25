package com.thinkx.ada.util

import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

object DateTimeUtils {

    private val TIME_FORMATTER = DateTimeFormatter.ofPattern("h:mm a", Locale.US)
    private val DATE_SHORT_FORMATTER = DateTimeFormatter.ofPattern("EEE, MMM d", Locale.US)
    private val DATE_FULL_FORMATTER = DateTimeFormatter.ofPattern("EEEE, MMMM d, yyyy", Locale.US)

    fun localDateTimeToEpochMs(dateTime: LocalDateTime, zoneId: ZoneId = ZoneId.systemDefault()): Long {
        return dateTime.atZone(zoneId).toInstant().toEpochMilli()
    }

    fun epochMsToLocalDateTime(epochMs: Long, zoneId: ZoneId = ZoneId.systemDefault()): LocalDateTime {
        return Instant.ofEpochMilli(epochMs).atZone(zoneId).toLocalDateTime()
    }

    fun formatTime(epochMs: Long, zoneId: ZoneId = ZoneId.systemDefault()): String {
        return epochMsToLocalDateTime(epochMs, zoneId).format(TIME_FORMATTER)
    }

    fun formatTime(dateTime: LocalDateTime): String {
        return dateTime.format(TIME_FORMATTER)
    }

    fun formatDateShort(epochMs: Long, zoneId: ZoneId = ZoneId.systemDefault()): String {
        return epochMsToLocalDateTime(epochMs, zoneId).format(DATE_SHORT_FORMATTER)
    }

    fun formatDateShort(date: LocalDate): String {
        return date.format(DATE_SHORT_FORMATTER)
    }

    fun formatDateFull(epochMs: Long, zoneId: ZoneId = ZoneId.systemDefault()): String {
        return epochMsToLocalDateTime(epochMs, zoneId).format(DATE_FULL_FORMATTER)
    }

    fun formatCountdown(targetEpochMs: Long, currentEpochMs: Long = System.currentTimeMillis()): String {
        val diffMs = targetEpochMs - currentEpochMs
        if (diffMs <= 0) return "Passed"

        val totalMinutes = (diffMs / 60000L).toInt()
        val hours = totalMinutes / 60
        val minutes = totalMinutes % 60
        val days = hours / 24
        val remHours = hours % 24

        return when {
            days > 0 -> "in ${days}d ${remHours}h"
            hours > 0 -> "in ${hours}h ${minutes}m"
            minutes > 0 -> "in ${minutes}m"
            else -> "in less than a min"
        }
    }
}
