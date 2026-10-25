package com.thinkx.ada.alarm.scheduler

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import com.thinkx.ada.MainActivity
import com.thinkx.ada.alarm.receiver.AlarmReceiver
import com.thinkx.ada.data.local.entity.AlarmEntity

class AndroidAlarmScheduler(
    private val context: Context,
    private val alarmManager: AlarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
) : AlarmScheduler {

    companion object {
        private const val TAG = "AdaAlarmScheduler"
    }

    override fun canScheduleExactAlarms(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            alarmManager.canScheduleExactAlarms()
        } else {
            true
        }
    }

    override fun schedule(alarm: AlarmEntity): ScheduleResult {
        if (!alarm.isEnabled) {
            cancel(alarm.id)
            return ScheduleResult.Success(alarm.scheduledAlarmEpochMs, alarm.id)
        }

        if (!canScheduleExactAlarms()) {
            Log.w(TAG, "Exact alarm scheduling permission is not granted on this device.")
            return ScheduleResult.PermissionDenied
        }

        val nowEpochMs = System.currentTimeMillis()
        if (alarm.scheduledAlarmEpochMs <= nowEpochMs) {
            Log.w(TAG, "Attempted to schedule alarm in the past: ${alarm.scheduledAlarmEpochMs} <= $nowEpochMs")
            return ScheduleResult.PastTime(alarm.scheduledAlarmEpochMs, nowEpochMs)
        }

        return try {
            val requestCode = alarm.id.hashCode()

            // 1. Alarm Broadcast Intent triggered when AlarmManager fires
            val triggerIntent = Intent(context, AlarmReceiver::class.java).apply {
                action = AlarmReceiver.ACTION_FIRE_ALARM
                putExtra(AlarmReceiver.EXTRA_ALARM_ID, alarm.id)
                putExtra(AlarmReceiver.EXTRA_ALARM_TITLE, alarm.title)
                putExtra(AlarmReceiver.EXTRA_DESTINATION_NAME, alarm.destinationName)
                putExtra(AlarmReceiver.EXTRA_SCHEDULED_TIME, alarm.scheduledAlarmEpochMs)
            }

            val triggerPendingIntent = PendingIntent.getBroadcast(
                context,
                requestCode,
                triggerIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            // 2. Show Intent displayed when user taps upcoming alarm in system clock/lockscreen
            val showIntent = Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra(AlarmReceiver.EXTRA_ALARM_ID, alarm.id)
            }

            val showPendingIntent = PendingIntent.getActivity(
                context,
                requestCode,
                showIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            // 3. Register with Android platform using setAlarmClock
            val alarmClockInfo = AlarmManager.AlarmClockInfo(
                alarm.scheduledAlarmEpochMs,
                showPendingIntent
            )

            alarmManager.setAlarmClock(alarmClockInfo, triggerPendingIntent)
            Log.i(TAG, "Successfully scheduled alarm ID=${alarm.id} at ${alarm.scheduledAlarmEpochMs}")
            ScheduleResult.Success(alarm.scheduledAlarmEpochMs, alarm.id)
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException scheduling exact alarm: ${e.message}", e)
            ScheduleResult.PermissionDenied
        } catch (e: Exception) {
            Log.e(TAG, "Failed to schedule alarm ID=${alarm.id}: ${e.message}", e)
            ScheduleResult.Error(e.message ?: "Unknown scheduling error", e)
        }
    }

    override fun cancel(alarmId: String): Boolean {
        return try {
            val requestCode = alarmId.hashCode()
            val triggerIntent = Intent(context, AlarmReceiver::class.java).apply {
                action = AlarmReceiver.ACTION_FIRE_ALARM
            }

            val triggerPendingIntent = PendingIntent.getBroadcast(
                context,
                requestCode,
                triggerIntent,
                PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE
            )

            if (triggerPendingIntent != null) {
                alarmManager.cancel(triggerPendingIntent)
                triggerPendingIntent.cancel()
                Log.i(TAG, "Cancelled alarm ID=$alarmId")
            }
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to cancel alarm ID=$alarmId: ${e.message}", e)
            false
        }
    }
}
