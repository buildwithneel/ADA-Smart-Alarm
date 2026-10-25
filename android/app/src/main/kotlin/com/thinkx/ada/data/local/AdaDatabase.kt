package com.thinkx.ada.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.thinkx.ada.data.local.dao.AlarmDao
import com.thinkx.ada.data.local.dao.DestinationDao
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.local.entity.DestinationEntity

@Database(
    entities = [
        AlarmEntity::class,
        DestinationEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class AdaDatabase : RoomDatabase() {

    abstract fun alarmDao(): AlarmDao
    abstract fun destinationDao(): DestinationDao

    companion object {
        private const val DATABASE_NAME = "ada_smart_alarm.db"

        @Volatile
        private var INSTANCE: AdaDatabase? = null

        fun getInstance(context: Context): AdaDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AdaDatabase::class.java,
                    DATABASE_NAME
                )
                    .fallbackToDestructiveMigration(true)
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
