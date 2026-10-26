package com.thinkx.ada.data.local

import androidx.sqlite.db.SupportSQLiteDatabase
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.lang.reflect.InvocationHandler
import java.lang.reflect.Method
import java.lang.reflect.Proxy

/**
 * Validates Room schema migrations across versions 1, 2, and 3.
 * Ensures that existing user alarms and destinations are never destroyed
 * during app updates, and all required columns and data backfills are executed.
 */
class RoomMigrationTest {

    private class RecordingDbHandler : InvocationHandler {
        val executedSql = mutableListOf<String>()

        override fun invoke(proxy: Any?, method: Method, args: Array<out Any>?): Any? {
            if (method.name == "execSQL" && args != null && args.isNotEmpty()) {
                executedSql.add(args[0] as String)
            }
            return null
        }
    }

    private fun createRecordingDb(): Pair<SupportSQLiteDatabase, RecordingDbHandler> {
        val handler = RecordingDbHandler()
        val proxy = Proxy.newProxyInstance(
            SupportSQLiteDatabase::class.java.classLoader,
            arrayOf(SupportSQLiteDatabase::class.java),
            handler
        ) as SupportSQLiteDatabase
        return Pair(proxy, handler)
    }

    @Test
    fun migration_1_to_2_addsSyncColumnsWithoutDroppingTables() {
        val (db, handler) = createRecordingDb()

        AdaDatabase.MIGRATION_1_2.migrate(db)

        val sqlList = handler.executedSql
        assertEquals(5, sqlList.size)
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN serverId TEXT") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN syncStatus TEXT NOT NULL DEFAULT 'PENDING'") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN lastSyncedEpochMs INTEGER") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE destinations ADD COLUMN serverId TEXT") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE destinations ADD COLUMN isSynced INTEGER NOT NULL DEFAULT 0") })
    }

    @Test
    fun migration_2_to_3_addsJourneyTrackingColumnsAndBackfillsScheduledDeparture() {
        val (db, handler) = createRecordingDb()

        AdaDatabase.MIGRATION_2_3.migrate(db)

        val sqlList = handler.executedSql
        // 17 ALTER TABLE statements + 1 UPDATE backfill = 18 statements
        assertEquals(18, sqlList.size)

        // Verify core journey tracking additions
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN scheduledDepartureEpochMs INTEGER NOT NULL DEFAULT 0") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN trackingLeadMinutes INTEGER NOT NULL DEFAULT 15") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN approachingThresholdMeters INTEGER NOT NULL DEFAULT 1000") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN arrivalThresholdMeters INTEGER NOT NULL DEFAULT 100") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN originAddress TEXT") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN currentEtaEpochMs INTEGER") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN lastLocationLat REAL") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN lastLocationLng REAL") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN remainingDistanceMeters INTEGER") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN remainingDurationSeconds INTEGER") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN isTrafficAware INTEGER NOT NULL DEFAULT 0") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN etaSource TEXT NOT NULL DEFAULT 'FALLBACK'") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN isApproachingAlertSent INTEGER NOT NULL DEFAULT 0") })
        assertTrue(sqlList.any { it.contains("ALTER TABLE alarms ADD COLUMN isArrivalConfirmed INTEGER NOT NULL DEFAULT 0") })

        // Verify existing user data backfill
        assertTrue(sqlList.any { it.contains("UPDATE alarms SET scheduledDepartureEpochMs = scheduledAlarmEpochMs WHERE scheduledDepartureEpochMs = 0") })
    }

    @Test
    fun migration_1_to_3_chainsBothMigrationsCleanly() {
        val (db, handler) = createRecordingDb()

        AdaDatabase.MIGRATION_1_3.migrate(db)

        val sqlList = handler.executedSql
        // 5 from 1->2 + 18 from 2->3 = 23 statements
        assertEquals(23, sqlList.size)
    }
}
