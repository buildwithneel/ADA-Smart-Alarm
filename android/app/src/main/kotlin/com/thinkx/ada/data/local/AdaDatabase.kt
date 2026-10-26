package com.thinkx.ada.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.thinkx.ada.data.local.dao.AlarmDao
import com.thinkx.ada.data.local.dao.DestinationDao
import com.thinkx.ada.data.local.entity.AlarmEntity
import com.thinkx.ada.data.local.entity.DestinationEntity

@Database(
    entities = [
        AlarmEntity::class,
        DestinationEntity::class
    ],
    version = 3,
    exportSchema = false
)
abstract class AdaDatabase : RoomDatabase() {

    abstract fun alarmDao(): AlarmDao
    abstract fun destinationDao(): DestinationDao

    companion object {
        private const val DATABASE_NAME = "ada_smart_alarm.db"

        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE alarms ADD COLUMN serverId TEXT DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN syncStatus TEXT NOT NULL DEFAULT 'PENDING'")
                db.execSQL("ALTER TABLE alarms ADD COLUMN lastSyncedEpochMs INTEGER DEFAULT NULL")

                db.execSQL("ALTER TABLE destinations ADD COLUMN serverId TEXT DEFAULT NULL")
                db.execSQL("ALTER TABLE destinations ADD COLUMN isSynced INTEGER NOT NULL DEFAULT 0")
            }
        }

        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE alarms ADD COLUMN scheduledDepartureEpochMs INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE alarms ADD COLUMN trackingLeadMinutes INTEGER NOT NULL DEFAULT 15")
                db.execSQL("ALTER TABLE alarms ADD COLUMN approachingThresholdMeters INTEGER NOT NULL DEFAULT 1000")
                db.execSQL("ALTER TABLE alarms ADD COLUMN arrivalThresholdMeters INTEGER NOT NULL DEFAULT 100")
                db.execSQL("ALTER TABLE alarms ADD COLUMN originAddress TEXT DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN currentEtaEpochMs INTEGER DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN lastLocationLat REAL DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN lastLocationLng REAL DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN lastLocationEpochMs INTEGER DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN remainingDistanceMeters INTEGER DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN remainingDurationSeconds INTEGER DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN isTrafficAware INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE alarms ADD COLUMN etaSource TEXT NOT NULL DEFAULT 'FALLBACK'")
                db.execSQL("ALTER TABLE alarms ADD COLUMN isApproachingAlertSent INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE alarms ADD COLUMN isArrivalConfirmed INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE alarms ADD COLUMN trackingStartedEpochMs INTEGER DEFAULT NULL")
                db.execSQL("ALTER TABLE alarms ADD COLUMN arrivalConfirmedEpochMs INTEGER DEFAULT NULL")
                db.execSQL("UPDATE alarms SET scheduledDepartureEpochMs = scheduledAlarmEpochMs WHERE scheduledDepartureEpochMs = 0")
            }
        }

        val MIGRATION_1_3 = object : Migration(1, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                MIGRATION_1_2.migrate(db)
                MIGRATION_2_3.migrate(db)
            }
        }

        @Volatile
        private var INSTANCE: AdaDatabase? = null

        fun getInstance(context: Context): AdaDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AdaDatabase::class.java,
                    DATABASE_NAME
                )
                    .addMigrations(MIGRATION_1_2, MIGRATION_2_3, MIGRATION_1_3)
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
