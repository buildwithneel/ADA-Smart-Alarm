package com.thinkx.ada

import android.app.Application
import com.thinkx.ada.alarm.scheduler.AlarmScheduler
import com.thinkx.ada.alarm.scheduler.AndroidAlarmScheduler
import com.thinkx.ada.data.local.AdaDatabase
import com.thinkx.ada.data.preferences.UserPreferencesRepository
import com.thinkx.ada.data.repository.AlarmRepository
import com.thinkx.ada.data.repository.AlarmRepositoryImpl
import com.thinkx.ada.data.repository.DestinationRepository
import com.thinkx.ada.data.repository.DestinationRepositoryImpl

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

    override fun onCreate() {
        super.onCreate()
        database = AdaDatabase.getInstance(this)
        alarmRepository = AlarmRepositoryImpl(database.alarmDao())
        destinationRepository = DestinationRepositoryImpl(database.destinationDao())
        userPreferencesRepository = UserPreferencesRepository(this)
        alarmScheduler = AndroidAlarmScheduler(this)
    }
}
