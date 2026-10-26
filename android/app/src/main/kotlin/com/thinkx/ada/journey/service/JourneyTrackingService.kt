package com.thinkx.ada.journey.service

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.thinkx.ada.AdaApplication
import com.thinkx.ada.MainActivity
import com.thinkx.ada.R
import com.thinkx.ada.data.local.AdaDatabase
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.domain.journey.model.JourneyAlertEvent
import com.thinkx.ada.domain.journey.model.JourneyLocationFix
import com.thinkx.ada.domain.journey.routing.CompositeRoutingProvider
import com.thinkx.ada.domain.journey.routing.FallbackRoutingProvider
import com.thinkx.ada.domain.journey.routing.BackendRoutingProvider
import com.thinkx.ada.journey.repository.JourneyTrackingCoordinator
import com.thinkx.ada.journey.repository.TrackingUpdateResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

class JourneyTrackingService : Service(), LocationListener {

    companion object {
        const val ACTION_START_TRACKING = "com.thinkx.ada.action.START_TRACKING"
        const val ACTION_STOP_TRACKING = "com.thinkx.ada.action.STOP_TRACKING"

        const val EXTRA_JOURNEY_ID = "extra_journey_id"
        const val EXTRA_JOURNEY_TITLE = "extra_journey_title"
        const val EXTRA_DESTINATION_NAME = "extra_destination_name"
        const val EXTRA_DESTINATION_LAT = "extra_destination_lat"
        const val EXTRA_DESTINATION_LNG = "extra_destination_lng"
        const val EXTRA_APPROACHING_THRESHOLD_METERS = "extra_approaching_threshold_meters"
        const val EXTRA_ARRIVAL_THRESHOLD_METERS = "extra_arrival_threshold_meters"

        private const val TAG = "AdaJourneyTrackingSvc"
        private const val NOTIFICATION_ID = 4001
        private const val APPROACHING_NOTIFICATION_ID = 4002
        private const val ARRIVAL_NOTIFICATION_ID = 4003

        private const val CHANNEL_TRACKING = "ada_journey_tracking_channel"
        private const val CHANNEL_ALERTS = "ada_journey_alerts_channel"

        private const val TARGET_LOCATION_INTERVAL_MS = 60_000L // 60 seconds target interval
        private const val MIN_DISTANCE_METERS = 10f
    }

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var locationManager: LocationManager? = null
    private var coordinator: JourneyTrackingCoordinator? = null

    private var activeJourneyId: String? = null
    private var destinationName: String = "Destination"
    private var journeyTitle: String = "Journey"

    override fun onCreate() {
        super.onCreate()
        locationManager = getSystemService(Context.LOCATION_SERVICE) as? LocationManager
        createNotificationChannels()

        val app = applicationContext as? AdaApplication
        val db = AdaDatabase.getInstance(applicationContext)
        val apiService = app?.apiService
        val routingProvider = if (apiService != null) {
            CompositeRoutingProvider(
                primary = BackendRoutingProvider(apiService),
                fallback = FallbackRoutingProvider()
            )
        } else {
            FallbackRoutingProvider()
        }

        coordinator = JourneyTrackingCoordinator(db.alarmDao(), routingProvider)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action ?: return START_NOT_STICKY

        when (action) {
            ACTION_START_TRACKING -> {
                val journeyId = intent.getStringExtra(EXTRA_JOURNEY_ID) ?: return START_NOT_STICKY
                activeJourneyId = journeyId
                destinationName = intent.getStringExtra(EXTRA_DESTINATION_NAME) ?: "Destination"
                journeyTitle = intent.getStringExtra(EXTRA_JOURNEY_TITLE) ?: "Trip to $destinationName"

                startForegroundTracking()
            }
            ACTION_STOP_TRACKING -> {
                stopTrackingSession(AlarmEntity.STATUS_STOPPED)
            }
        }

        return START_STICKY
    }

    private fun startForegroundTracking() {
        val initialNotification = buildTrackingNotification(
            statusText = "Tracking active • Waiting for initial GPS fix..."
        )
        startForeground(NOTIFICATION_ID, initialNotification)
        requestGpsUpdates()
    }

    private fun requestGpsUpdates() {
        if (locationManager == null) {
            Log.e(TAG, "LocationManager unavailable")
            return
        }

        val fineGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        val coarseGranted = ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (!fineGranted && !coarseGranted) {
            Log.e(TAG, "Location permission missing; cannot track GPS")
            stopTrackingSession(AlarmEntity.STATUS_FAILED)
            return
        }

        try {
            // Target 60-second updates from GPS Provider
            if (locationManager?.isProviderEnabled(LocationManager.GPS_PROVIDER) == true) {
                locationManager?.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER,
                    TARGET_LOCATION_INTERVAL_MS,
                    MIN_DISTANCE_METERS,
                    this
                )
            }

            // Also register Network provider as fallback in urban canyons / indoor situations
            if (locationManager?.isProviderEnabled(LocationManager.NETWORK_PROVIDER) == true) {
                locationManager?.requestLocationUpdates(
                    LocationManager.NETWORK_PROVIDER,
                    TARGET_LOCATION_INTERVAL_MS,
                    MIN_DISTANCE_METERS,
                    this
                )
            }

            Log.i(TAG, "Registered location updates at target 60s interval")
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException requesting location updates: ${e.message}", e)
            stopTrackingSession(AlarmEntity.STATUS_FAILED)
        }
    }

    override fun onLocationChanged(location: Location) {
        val journeyId = activeJourneyId ?: return
        val coordinator = coordinator ?: return

        val fix = JourneyLocationFix(
            latitude = location.latitude,
            longitude = location.longitude,
            accuracyMeters = location.accuracy,
            timestampEpochMs = location.time,
            speedMps = if (location.hasSpeed()) location.speed else null,
            bearingDegrees = if (location.hasBearing()) location.bearing else null
        )

        serviceScope.launch {
            try {
                val result = coordinator.processLocationFix(journeyId, fix)
                handleTrackingUpdate(result)
            } catch (e: Exception) {
                Log.e(TAG, "Error in coordinator processing fix: ${e.message}", e)
            }
        }
    }

    private fun handleTrackingUpdate(result: TrackingUpdateResult) {
        val eta = result.etaResult
        val statusText = if (eta != null) {
            val formatter = DateTimeFormatter.ofPattern("h:mm a").withZone(ZoneId.systemDefault())
            val etaFormatted = formatter.format(Instant.ofEpochMilli(eta.predictedArrivalEpochMs))
            val distKm = "%.1f".format(result.remainingDistanceMeters / 1000.0)
            val trafficLabel = if (eta.isTrafficAware) "Traffic-aware" else "Estimate"
            "ETA: $etaFormatted • $distKm km • $trafficLabel"
        } else {
            "Tracking active • Calculating route..."
        }

        // Update foreground notification
        val notification = buildTrackingNotification(statusText)
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
        nm?.notify(NOTIFICATION_ID, notification)

        // Handle Alert Events
        when (result.alertEvent) {
            JourneyAlertEvent.APPROACHING_ALERT -> {
                sendApproachingNotification(result.remainingDistanceMeters)
            }
            JourneyAlertEvent.ARRIVAL_CONFIRMED -> {
                sendArrivalNotification()
                stopTrackingSession(AlarmEntity.STATUS_ARRIVED)
            }
            null -> Unit
        }
    }

    private fun sendApproachingNotification(distanceMeters: Int) {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return
        val pendingIntent = PendingIntent.getActivity(
            this,
            APPROACHING_NOTIFICATION_ID,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ALERTS)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("Approaching $destinationName")
            .setContentText("You are approximately ${distanceMeters}m from your destination.")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setDefaults(Notification.DEFAULT_ALL)
            .build()

        nm.notify(APPROACHING_NOTIFICATION_ID, notification)
        Log.i(TAG, "Delivered Approaching Destination Alert")
    }

    private fun sendArrivalNotification() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return
        val pendingIntent = PendingIntent.getActivity(
            this,
            ARRIVAL_NOTIFICATION_ID,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ALERTS)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle("Arrived at $destinationName")
            .setContentText("Journey completed. Tracking has stopped.")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setDefaults(Notification.DEFAULT_ALL)
            .build()

        nm.notify(ARRIVAL_NOTIFICATION_ID, notification)
        Log.i(TAG, "Delivered Arrival Confirmation Alert")
    }

    private fun stopTrackingSession(finalStatus: String) {
        val journeyId = activeJourneyId
        Log.i(TAG, "Stopping tracking session for journey $journeyId with status: $finalStatus")

        try {
            locationManager?.removeUpdates(this)
        } catch (e: Exception) {
            Log.w(TAG, "Error removing location updates: ${e.message}")
        }

        if (journeyId != null) {
            serviceScope.launch(Dispatchers.IO) {
                try {
                    val db = AdaDatabase.getInstance(applicationContext)
                    db.alarmDao().updateAlarmStatus(journeyId, finalStatus, System.currentTimeMillis())
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to update terminal status for journey $journeyId: ${e.message}")
                }
            }
        }

        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun buildTrackingNotification(statusText: String): Notification {
        val openAppIntent = PendingIntent.getActivity(
            this,
            NOTIFICATION_ID,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val stopIntent = Intent(this, JourneyTrackingService::class.java).apply {
            action = ACTION_STOP_TRACKING
        }
        val stopPendingIntent = PendingIntent.getService(
            this,
            NOTIFICATION_ID + 10,
            stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_TRACKING)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(journeyTitle)
            .setContentText(statusText)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(openAppIntent)
            .addAction(R.drawable.ic_launcher_foreground, "Stop Tracking", stopPendingIntent)
            .build()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager ?: return

            val trackingChannel = NotificationChannel(
                CHANNEL_TRACKING,
                "ADA Journey Live Tracking",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows live journey progress, remaining distance, and traffic-aware dynamic ETA"
                setShowBadge(false)
            }

            val alertsChannel = NotificationChannel(
                CHANNEL_ALERTS,
                "ADA Journey Approaching & Arrival Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifies when approaching destination or confirming arrival"
                enableVibration(true)
            }

            nm.createNotificationChannel(trackingChannel)
            nm.createNotificationChannel(alertsChannel)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        locationManager?.removeUpdates(this)
        serviceScope.cancel()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // LocationListener stubs for backwards compatibility with older Android versions
    @Deprecated("Deprecated in Java")
    override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
    override fun onProviderEnabled(provider: String) {}
    override fun onProviderDisabled(provider: String) {}
}
