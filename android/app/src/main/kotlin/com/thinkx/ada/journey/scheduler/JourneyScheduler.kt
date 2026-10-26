package com.thinkx.ada.journey.scheduler

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import com.thinkx.ada.MainActivity
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.journey.receiver.JourneyStartReceiver

interface JourneyScheduler {
    fun scheduleTrackingStart(journey: AlarmEntity): Boolean
    fun cancelTrackingStart(journeyId: String)
    fun canScheduleExactAlarms(): Boolean
}

class AndroidJourneyScheduler(
    private val context: Context
) : JourneyScheduler {

    companion object {
        private const val TAG = "AdaJourneyScheduler"
    }

    private val alarmManager: AlarmManager? =
        context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager

    override fun canScheduleExactAlarms(): Boolean {
        if (alarmManager == null) return false
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            alarmManager.canScheduleExactAlarms()
        } else {
            true
        }
    }

    override fun scheduleTrackingStart(journey: AlarmEntity): Boolean {
        if (alarmManager == null) {
            Log.e(TAG, "AlarmManager service unavailable")
            return false
        }

        if (!canScheduleExactAlarms()) {
            Log.w(TAG, "Exact alarm permission missing; cannot schedule journey tracking start")
            return false
        }

        val trackingStartTimeEpochMs = journey.trackingStartAttemptEpochMs
        val nowEpochMs = System.currentTimeMillis()

        if (trackingStartTimeEpochMs <= nowEpochMs) {
            Log.w(TAG, "Tracking start time is in the past ($trackingStartTimeEpochMs <= $nowEpochMs); scheduling immediate attempt")
        }

        val intent = Intent(context, JourneyStartReceiver::class.java).apply {
            action = JourneyStartReceiver.ACTION_START_JOURNEY_TRACKING
            putExtra(JourneyStartReceiver.EXTRA_JOURNEY_ID, journey.id)
            putExtra(JourneyStartReceiver.EXTRA_JOURNEY_TITLE, journey.title)
            putExtra(JourneyStartReceiver.EXTRA_DESTINATION_NAME, journey.destinationName)
        }

        val requestCode = journey.id.hashCode()
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        val pendingIntent = PendingIntent.getBroadcast(context, requestCode, intent, flags)

        val showIntent = PendingIntent.getActivity(
            context,
            requestCode,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val alarmClockInfo = AlarmManager.AlarmClockInfo(trackingStartTimeEpochMs, showIntent)

        try {
            alarmManager.setAlarmClock(alarmClockInfo, pendingIntent)
            Log.i(
                TAG,
                "Scheduled tracking start for journey '${journey.title}' (ID: ${journey.id}) at epoch ms: $trackingStartTimeEpochMs"
            )
            return true
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException scheduling tracking start: ${e.message}", e)
            return false
        }
    }

    override fun cancelTrackingStart(journeyId: String) {
        if (alarmManager == null) return

        val intent = Intent(context, JourneyStartReceiver::class.java).apply {
            action = JourneyStartReceiver.ACTION_START_JOURNEY_TRACKING
        }
        val requestCode = journeyId.hashCode()
        val flags = PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE
        val pendingIntent = PendingIntent.getBroadcast(context, requestCode, intent, flags)

        if (pendingIntent != null) {
            alarmManager.cancel(pendingIntent)
            pendingIntent.cancel()
            Log.i(TAG, "Cancelled tracking start for journey ID: $journeyId")
        }
    }
}
