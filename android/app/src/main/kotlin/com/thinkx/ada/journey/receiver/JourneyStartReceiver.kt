package com.thinkx.ada.journey.receiver

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.PowerManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.thinkx.ada.data.local.AdaDatabase
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.journey.service.JourneyTrackingService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class JourneyStartReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_START_JOURNEY_TRACKING = "com.thinkx.ada.action.START_JOURNEY_TRACKING"
        const val EXTRA_JOURNEY_ID = "extra_journey_id"
        const val EXTRA_JOURNEY_TITLE = "extra_journey_title"
        const val EXTRA_DESTINATION_NAME = "extra_destination_name"

        private const val TAG = "AdaJourneyStartReceiver"
        private const val WAKELOCK_TIMEOUT_MS = 30_000L
    }

    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        if (action != ACTION_START_JOURNEY_TRACKING) return

        val journeyId = intent.getStringExtra(EXTRA_JOURNEY_ID) ?: return
        Log.i(TAG, "JourneyStartReceiver fired for journey ID: $journeyId")

        val powerManager = context.getSystemService(Context.POWER_SERVICE) as? PowerManager
        val wakeLock = powerManager?.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "ada:journey_start_wakelock")
        wakeLock?.acquire(WAKELOCK_TIMEOUT_MS)

        val pendingResult = goAsync()

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val db = AdaDatabase.getInstance(context)
                val journey = db.alarmDao().getAlarmById(journeyId)

                if (journey == null) {
                    Log.w(TAG, "Journey $journeyId not found in database; aborting start")
                    return@launch
                }

                if (!journey.isEnabled || journey.status == AlarmEntity.STATUS_CANCELLED) {
                    Log.i(TAG, "Journey $journeyId is disabled or cancelled; skipping tracking")
                    return@launch
                }

                // Check Location permission
                val fineLocationGranted = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_FINE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED
                val coarseLocationGranted = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED

                if (!fineLocationGranted && !coarseLocationGranted) {
                    Log.e(TAG, "Location permission missing when starting journey $journeyId. Marking FAILED.")
                    db.alarmDao().updateAlarmStatus(journeyId, AlarmEntity.STATUS_FAILED, System.currentTimeMillis())
                    return@launch
                }

                // Start JourneyTrackingService
                val serviceIntent = Intent(context, JourneyTrackingService::class.java).apply {
                    this.action = JourneyTrackingService.ACTION_START_TRACKING
                    putExtra(JourneyTrackingService.EXTRA_JOURNEY_ID, journeyId)
                    putExtra(JourneyTrackingService.EXTRA_JOURNEY_TITLE, journey.title)
                    putExtra(JourneyTrackingService.EXTRA_DESTINATION_NAME, journey.destinationName)
                    putExtra(JourneyTrackingService.EXTRA_DESTINATION_LAT, journey.destinationLat)
                    putExtra(JourneyTrackingService.EXTRA_DESTINATION_LNG, journey.destinationLng)
                    putExtra(JourneyTrackingService.EXTRA_APPROACHING_THRESHOLD_METERS, journey.approachingThresholdMeters)
                    putExtra(JourneyTrackingService.EXTRA_ARRIVAL_THRESHOLD_METERS, journey.arrivalThresholdMeters)
                }

                ContextCompat.startForegroundService(context, serviceIntent)
                Log.i(TAG, "Successfully requested startForegroundService for journey $journeyId")
            } catch (e: Exception) {
                Log.e(TAG, "Error initiating journey tracking: ${e.message}", e)
            } finally {
                if (wakeLock?.isHeld == true) {
                    wakeLock.release()
                }
                pendingResult.finish()
            }
        }
    }
}
