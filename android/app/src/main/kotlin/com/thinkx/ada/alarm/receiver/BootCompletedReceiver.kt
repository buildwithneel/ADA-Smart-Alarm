package com.thinkx.ada.alarm.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.thinkx.ada.alarm.recovery.AlarmRecoveryManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class BootCompletedReceiver : BroadcastReceiver() {

    companion object {
        private const val TAG = "AdaBootReceiver"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == "android.intent.action.QUICKBOOT_POWERON" ||
            intent.action == "com.htc.intent.action.QUICKBOOT_POWERON"
        ) {
            Log.i(TAG, "Device reboot detected (${intent.action}). Re-arming eligible ADA alarms...")

            val pendingResult = goAsync()
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val recoveryManager = AlarmRecoveryManager.create(context)
                    val result = recoveryManager.rearmAllEligibleAlarms()
                    Log.i(TAG, "Reboot recovery completed: rearmed=${result.rearmedCount}, failures=${result.failureCount}")
                } catch (e: Exception) {
                    Log.e(TAG, "Error re-arming alarms after reboot: ${e.message}", e)
                } finally {
                    pendingResult.finish()
                }
            }
        }
    }
}
