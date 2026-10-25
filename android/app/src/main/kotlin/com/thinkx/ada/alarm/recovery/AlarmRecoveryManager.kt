package com.thinkx.ada.alarm.recovery

import android.content.Context
import android.util.Log
import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.alarm.scheduler.AndroidAlarmScheduler
import com.thinkx.ada.alarm.scheduler.ScheduleResult
import com.thinkx.ada.data.local.AdaDatabase
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.repository.AlarmRepository
import com.thinkx.ada.data.repository.AlarmRepositoryImpl

data class RecoveryResult(
    val totalChecked: Int,
    val rearmedCount: Int,
    val expiredCount: Int,
    val failureCount: Int
)

class AlarmRecoveryManager(
    private val alarmRepository: AlarmRepository,
    private val alarmScheduler: AlarmScheduler
) {

    companion object {
        private const val TAG = "AdaAlarmRecovery"

        fun create(context: Context): AlarmRecoveryManager {
            val db = AdaDatabase.getInstance(context)
            val repo = AlarmRepositoryImpl(db.alarmDao())
            val scheduler = AndroidAlarmScheduler(context)
            return AlarmRecoveryManager(repo, scheduler)
        }
    }

    suspend fun rearmAllEligibleAlarms(nowEpochMs: Long = System.currentTimeMillis()): RecoveryResult {
        Log.i(TAG, "Starting alarm reconciliation and re-arming process at $nowEpochMs")

        if (!alarmScheduler.canScheduleExactAlarms()) {
            Log.w(TAG, "Exact alarm scheduling permission unavailable. Cannot re-arm alarms.")
            return RecoveryResult(totalChecked = 0, rearmedCount = 0, expiredCount = 0, failureCount = 0)
        }

        val enabledAlarms = alarmRepository.getEnabledAlarms()
        var rearmedCount = 0
        var expiredCount = 0
        var failureCount = 0

        for (alarm in enabledAlarms) {
            if (alarm.scheduledAlarmEpochMs > nowEpochMs) {
                // Future alarm: re-arm with platform AlarmManager
                when (val result = alarmScheduler.schedule(alarm)) {
                    is ScheduleResult.Success -> {
                        rearmedCount++
                        Log.i(TAG, "Re-armed alarm ID=${alarm.id} at ${alarm.scheduledAlarmEpochMs}")
                    }
                    else -> {
                        failureCount++
                        Log.e(TAG, "Failed to re-arm alarm ID=${alarm.id}: $result")
                    }
                }
            } else {
                // Past alarm: if one-time, mark dismissed; if repeating, leave for periodic scheduler
                if (alarm.isOneTime) {
                    alarmRepository.dismissAlarm(alarm.id)
                    expiredCount++
                    Log.i(TAG, "Expired one-time alarm ID=${alarm.id} marked as dismissed.")
                }
            }
        }

        Log.i(TAG, "Reconciliation finished: checked=${enabledAlarms.size}, rearmed=$rearmedCount, expired=$expiredCount, failures=$failureCount")
        return RecoveryResult(
            totalChecked = enabledAlarms.size,
            rearmedCount = rearmedCount,
            expiredCount = expiredCount,
            failureCount = failureCount
        )
    }
}
