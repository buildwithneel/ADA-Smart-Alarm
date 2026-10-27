package com.thinkx.ada.journey

import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.journey.scheduler.JourneyScheduler

/**
 * Deterministic in-memory fake implementation of [JourneyScheduler] for isolated unit testing.
 */
class FakeJourneyScheduler(
    var exactAlarmPermissionGranted: Boolean = true
) : JourneyScheduler {

    val scheduledJourneys = mutableMapOf<String, AlarmEntity>()
    val cancelledJourneyIds = mutableListOf<String>()

    override fun canScheduleExactAlarms(): Boolean = exactAlarmPermissionGranted

    override fun scheduleTrackingStart(journey: AlarmEntity): Boolean {
        if (!exactAlarmPermissionGranted) return false
        scheduledJourneys[journey.id] = journey
        return true
    }

    override fun cancelTrackingStart(journeyId: String) {
        cancelledJourneyIds.add(journeyId)
        scheduledJourneys.remove(journeyId)
    }

    fun clear() {
        scheduledJourneys.clear()
        cancelledJourneyIds.clear()
    }
}
