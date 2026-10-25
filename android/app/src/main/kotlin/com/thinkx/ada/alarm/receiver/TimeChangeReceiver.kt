package com.thinkx.ada.alarm.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.thinkx.ada.alarm.recovery.AlarmRecoveryManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class TimeChangeReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "AdaTimeChangeReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_TIME_CHANGED ||
            intent.action == Intent.ACTION_TIMEZONE_CHANGED
        ) {
            Log.i(TAG, "Time or TimeZone modification detected (${intent.action}). Reconciling ADA schedules...")

            val pendingResult = goAsync()
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val recoveryManager = AlarmRecoveryManager.create(context)
                    recoveryManager.rearmAllEligibleAlarms()
                } catch (e: Exception) {
                    Log.e(TAG, "Error reconciling alarms on time change: ${e.message}", e)
                } finally {
                    pendingResult.finish()
                }
            }
        }
    }
}
