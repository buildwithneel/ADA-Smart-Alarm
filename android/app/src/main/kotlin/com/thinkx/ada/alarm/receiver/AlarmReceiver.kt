package com.thinkx.ada.alarm.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.PowerManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.thinkx.ada.alarm.scheduler.AndroidAlarmScheduler
import com.thinkx.ada.alarm.service.AlarmService
import com.thinkx.ada.data.local.AdaDatabase
import com.thinkx.ada.data.repository.AlarmRepositoryImpl
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class AlarmReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_FIRE_ALARM = "com.thinkx.ada.action.FIRE_ALARM"
        const val ACTION_DISMISS_ALARM = "com.thinkx.ada.action.DISMISS_ALARM"
        const val ACTION_SNOOZE_ALARM = "com.thinkx.ada.action.SNOOZE_ALARM"

        const val EXTRA_ALARM_ID = "extra_alarm_id"
        const val EXTRA_ALARM_TITLE = "extra_alarm_title"
        const val EXTRA_DESTINATION_NAME = "extra_destination_name"
        const val EXTRA_SCHEDULED_TIME = "extra_scheduled_time"

        private const val TAG = "AdaAlarmReceiver"
        private const val WAKELOCK_TIMEOUT_MS = 10 * 60 * 1000L // 10 minutes max
    }

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        val alarmId = intent.getStringExtra(EXTRA_ALARM_ID) ?: return

        Log.i(TAG, "AlarmReceiver received action=$action for alarm ID=$alarmId")

        when (action) {
            ACTION_FIRE_ALARM -> handleFireAlarm(context, intent)
            ACTION_DISMISS_ALARM -> handleDismissAlarm(context, alarmId)
            ACTION_SNOOZE_ALARM -> handleSnoozeAlarm(context, alarmId)
        }
    }

    private fun handleFireAlarm(context: Context, intent: Intent) {
        // 1. Acquire temporary partial wake lock to guarantee CPU remains active while starting service
        val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
        val wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "ada:alarm_receiver_wake_lock"
        )
        wakeLock.acquire(WAKELOCK_TIMEOUT_MS)

        // 2. Start AlarmService as a foreground service
        val serviceIntent = Intent(context, AlarmService::class.java).apply {
            action = AlarmService.ACTION_START_RINGING
            putExtra(EXTRA_ALARM_ID, intent.getStringExtra(EXTRA_ALARM_ID))
            putExtra(EXTRA_ALARM_TITLE, intent.getStringExtra(EXTRA_ALARM_TITLE))
            putExtra(EXTRA_DESTINATION_NAME, intent.getStringExtra(EXTRA_DESTINATION_NAME))
        }

        try {
            ContextCompat.startForegroundService(context, serviceIntent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start AlarmService: ${e.message}", e)
        } finally {
            if (wakeLock.isHeld) {
                wakeLock.release()
            }
        }
    }

    private fun handleDismissAlarm(context: Context, alarmId: String) {
        // Stop the foreground ringing service
        val stopIntent = Intent(context, AlarmService::class.java).apply {
            action = AlarmService.ACTION_STOP_RINGING
        }
        context.startService(stopIntent)

        // Persist dismissed state in Room
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val db = AdaDatabase.getInstance(context)
                val repository = AlarmRepositoryImpl(db.alarmDao())
                repository.dismissAlarm(alarmId)
                Log.i(TAG, "Alarm ID=$alarmId successfully dismissed in database.")
            } catch (e: Exception) {
                Log.e(TAG, "Error dismissing alarm in database: ${e.message}", e)
            } finally {
                pendingResult.finish()
            }
        }
    }

    private fun handleSnoozeAlarm(context: Context, alarmId: String) {
        // Stop current ringing
        val stopIntent = Intent(context, AlarmService::class.java).apply {
            action = AlarmService.ACTION_STOP_RINGING
        }
        context.startService(stopIntent)

        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val db = AdaDatabase.getInstance(context)
                val repository = AlarmRepositoryImpl(db.alarmDao())
                val alarm = repository.getAlarmById(alarmId)

                if (alarm != null) {
                    val snoozeMinutes = alarm.snoozeLengthMinutes.coerceAtLeast(1)
                    val newScheduleEpochMs = System.currentTimeMillis() + (snoozeMinutes * 60 * 1000L)

                    // 1. Update database record
                    repository.snoozeAlarm(alarmId, newScheduleEpochMs)

                    // 2. Schedule new alarm with AlarmManager
                    val scheduler = AndroidAlarmScheduler(context)
                    val snoozedAlarm = alarm.copy(
                        scheduledAlarmEpochMs = newScheduleEpochMs,
                        isSnoozed = true,
                        snoozeCount = alarm.snoozeCount + 1,
                        status = "SNOOZED"
                    )
                    scheduler.schedule(snoozedAlarm)
                    Log.i(TAG, "Alarm ID=$alarmId snoozed for $snoozeMinutes min to $newScheduleEpochMs")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error snoozing alarm: ${e.message}", e)
            } finally {
                pendingResult.finish()
            }
        }
    }
}
