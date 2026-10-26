package com.thinkx.ada

import android.app.Application
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.alarm.scheduler.AndroidAlarmScheduler
import com.thinkx.ada.auth.repository.AuthRepository
import com.thinkx.ada.auth.repository.FirebaseAuthRepository
import com.thinkx.ada.data.local.AdaDatabase
import com.thinkx.ada.data.preferences.UserPreferencesRepository
import com.thinkx.ada.data.repository.AlarmRepository
import com.thinkx.ada.data.repository.AlarmRepositoryImpl
import com.thinkx.ada.data.repository.DestinationRepository
import com.thinkx.ada.data.repository.DestinationRepositoryImpl
import com.thinkx.ada.data.sync.AlarmSyncRepository
import com.thinkx.ada.data.sync.AlarmSyncRepositoryImpl
import com.thinkx.ada.network.ApiClient
import com.thinkx.ada.network.api.AdaApiService

class AdaApplication : Application() {

    lateinit var database: AdaDatabase
        private set

    lateinit var alarmRepository: AlarmRepository
        private set

    lateinit var destinationRepository: DestinationRepository
        private set

    lateinit var userPreferencesRepository: UserPreferencesRepository
        private set

    lateinit var alarmScheduler: AlarmScheduler
        private set

    lateinit var authRepository: AuthRepository
        private set

    lateinit var apiService: AdaApiService
        private set

    lateinit var syncRepository: AlarmSyncRepository
        private set

    lateinit var journeyScheduler: com.thinkx.ada.journey.scheduler.JourneyScheduler
        private set

    lateinit var routingProvider: com.thinkx.ada.domain.journey.routing.RoutingProvider
        private set

    override fun onCreate() {
        super.onCreate()

        // Initialize Firebase SDK if not automatically initialized
        initFirebase()

        database = AdaDatabase.getInstance(this)
        alarmRepository = AlarmRepositoryImpl(database.alarmDao())
        destinationRepository = DestinationRepositoryImpl(database.destinationDao())
        userPreferencesRepository = UserPreferencesRepository(this)
        alarmScheduler = AndroidAlarmScheduler(this)
        journeyScheduler = com.thinkx.ada.journey.scheduler.AndroidJourneyScheduler(this)

        authRepository = FirebaseAuthRepository()
        apiService = ApiClient.createApiService(authRepository)
        routingProvider = com.thinkx.ada.domain.journey.routing.CompositeRoutingProvider(
            primary = com.thinkx.ada.domain.journey.routing.BackendRoutingProvider(apiService),
            fallback = com.thinkx.ada.domain.journey.routing.FallbackRoutingProvider()
        )
        syncRepository = AlarmSyncRepositoryImpl(
            apiService = apiService,
            alarmDao = database.alarmDao(),
            destinationDao = database.destinationDao(),
            alarmScheduler = alarmScheduler
        )
    }

    private fun initFirebase() {
        try {
            if (FirebaseApp.getApps(this).isEmpty()) {
                val options = FirebaseOptions.Builder()
                    .setApplicationId(packageName)
                    .setApiKey("AIzaSyDummyKeyForDevelopmentPreview")
                    .setProjectId(BuildConfig.FIREBASE_PROJECT_ID)
                    .build()
                FirebaseApp.initializeApp(this, options)
            }
        } catch (_: Exception) {
            // Non-fatal: ensures local alarms continue even without cloud credentials
        }
    }
}
