package com.thinkx.ada.alarm.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Color
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.thinkx.ada.R
import com.thinkx.ada.alarm.playback.AlarmPlaybackManager
import com.thinkx.ada.alarm.receiver.AlarmReceiver
import com.thinkx.ada.alarm.ui.AlarmActivity

class AlarmService : Service() {

    companion object {
        const val CHANNEL_ID = "ada_alarm_channel_high_priority"
        const val CHANNEL_NAME = "ADA Smart Alarm"
        const val NOTIFICATION_ID = 4001
        private const val TAG = "AdaAlarmService"

        const val ACTION_START_RINGING = "com.thinkx.ada.action.START_RINGING"
        const val ACTION_STOP_RINGING = "com.thinkx.ada.action.STOP_RINGING"
    }

    private lateinit var playbackManager: AlarmPlaybackManager
    private var isRinging = false

    override fun onCreate() {
        super.onCreate()
        playbackManager = AlarmPlaybackManager(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action ?: ACTION_START_RINGING

        if (action == ACTION_STOP_RINGING) {
            stopRinging()
            stopSelf()
            return START_NOT_STICKY
        }

        val alarmId = intent?.getStringExtra(AlarmReceiver.EXTRA_ALARM_ID) ?: "unknown"
        val alarmTitle = intent?.getStringExtra(AlarmReceiver.EXTRA_ALARM_TITLE) ?: "Smart Alarm"
        val destinationName = intent?.getStringExtra(AlarmReceiver.EXTRA_DESTINATION_NAME) ?: "Destination"

        if (!isRinging) {
            isRinging = true
            val notification = buildAlarmNotification(alarmId, alarmTitle, destinationName)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(
                    NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
                )
            } else {
                startForeground(NOTIFICATION_ID, notification)
            }
            playbackManager.startPlayback()
            Log.i(TAG, "AlarmService ringing initiated for alarm ID=$alarmId")
        }

        return START_STICKY
    }

    private fun stopRinging() {
        if (isRinging) {
            playbackManager.stop()
            isRinging = false
            stopForeground(STOP_FOREGROUND_REMOVE)
            Log.i(TAG, "AlarmService ringing stopped and foreground removed.")
        }
    }

    override fun onDestroy() {
        stopRinging()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun buildAlarmNotification(
        alarmId: String,
        alarmTitle: String,
        destinationName: String
    ): Notification {
        // 1. Full Screen Intent to AlarmActivity
        val fullScreenIntent = Intent(this, AlarmActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_NO_USER_ACTION or
                    Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(AlarmReceiver.EXTRA_ALARM_ID, alarmId)
            putExtra(AlarmReceiver.EXTRA_ALARM_TITLE, alarmTitle)
            putExtra(AlarmReceiver.EXTRA_DESTINATION_NAME, destinationName)
        }

        val fullScreenPendingIntent = PendingIntent.getActivity(
            this,
            alarmId.hashCode(),
            fullScreenIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // 2. Dismiss Action Intent
        val dismissIntent = Intent(this, AlarmReceiver::class.java).apply {
            action = AlarmReceiver.ACTION_DISMISS_ALARM
            putExtra(AlarmReceiver.EXTRA_ALARM_ID, alarmId)
        }
        val dismissPendingIntent = PendingIntent.getBroadcast(
            this,
            (alarmId + "_dismiss").hashCode(),
            dismissIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // 3. Snooze Action Intent
        val snoozeIntent = Intent(this, AlarmReceiver::class.java).apply {
            action = AlarmReceiver.ACTION_SNOOZE_ALARM
            putExtra(AlarmReceiver.EXTRA_ALARM_ID, alarmId)
        }
        val snoozePendingIntent = PendingIntent.getBroadcast(
            this,
            (alarmId + "_snooze").hashCode(),
            snoozeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentTitle(alarmTitle)
            .setContentText("Time to wake up! Head to $destinationName")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOngoing(true)
            .setAutoCancel(false)
            .setFullScreenIntent(fullScreenPendingIntent, true)
            .setContentIntent(fullScreenPendingIntent)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Dismiss", dismissPendingIntent)
            .addAction(android.R.drawable.ic_popup_sync, "Snooze (10m)", snoozePendingIntent)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Critical ADA Smart Alarm ringing notifications"
                enableLights(true)
                lightColor = Color.RED
                enableVibration(true)
                setBypassDnd(true)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
                // Sound handled by AlarmPlaybackManager
                setSound(null, null)
            }
            notificationManager.createNotificationChannel(channel)
        }
    }
}
