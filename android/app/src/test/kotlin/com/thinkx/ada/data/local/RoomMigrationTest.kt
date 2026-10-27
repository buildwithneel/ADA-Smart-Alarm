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

    @Test
    fun migration_preserves_existing_user_data_and_correctly_backfills_v3_fields() {
        // Representative V1 user data
        val v1Alarms = mutableMapOf(
            "alarm-101" to mutableMapOf<String, Any?>(
                "id" to "alarm-101",
                "title" to "Morning Office Commute",
                "destinationName" to "Tech Park",
                "destinationAddress" to "100 Innovation Blvd",
                "destinationLat" to 37.7749,
                "destinationLng" to -122.4194,
                "scheduledAlarmEpochMs" to 1710000000000L,
                "requiredArrivalEpochMs" to 1710003600000L,
                "travelDurationMinutes" to 35,
                "isEnabled" to 1
            )
        )

        val v1Destinations = mutableMapOf(
            "dest-201" to mutableMapOf<String, Any?>(
                "id" to "dest-201",
                "name" to "HQ Office",
                "address" to "100 Innovation Blvd",
                "latitude" to 37.7749,
                "longitude" to -122.4194
            )
        )

        // Simulated SQLite executor that tracks schema changes and row mutations
        val simulatedDbHandler = object : InvocationHandler {
            override fun invoke(proxy: Any?, method: Method, args: Array<out Any>?): Any? {
                if (method.name == "execSQL" && args != null && args.isNotEmpty()) {
                    val sql = args[0] as String

                    // Parse ALTER TABLE ADD COLUMN
                    if (sql.startsWith("ALTER TABLE alarms ADD COLUMN")) {
                        val colDef = sql.removePrefix("ALTER TABLE alarms ADD COLUMN ").trim()
                        val colName = colDef.split(" ")[0]
                        val defaultVal = when {
                            colDef.contains("DEFAULT 'PENDING'") -> "PENDING"
                            colDef.contains("DEFAULT 'FALLBACK'") -> "FALLBACK"
                            colDef.contains("DEFAULT 1000") -> 1000
                            colDef.contains("DEFAULT 100") -> 100
                            colDef.contains("DEFAULT 15") -> 15
                            colDef.contains("DEFAULT 0") -> 0
                            else -> null
                        }
                        v1Alarms.values.forEach { row -> row[colName] = defaultVal }
                    } else if (sql.startsWith("ALTER TABLE destinations ADD COLUMN")) {
                        val colDef = sql.removePrefix("ALTER TABLE destinations ADD COLUMN ").trim()
                        val colName = colDef.split(" ")[0]
                        val defaultVal = if (colDef.contains("DEFAULT 0")) 0 else null
                        v1Destinations.values.forEach { row -> row[colName] = defaultVal }
                    } else if (sql.startsWith("UPDATE alarms SET scheduledDepartureEpochMs = scheduledAlarmEpochMs")) {
                        v1Alarms.values.forEach { row ->
                            if ((row["scheduledDepartureEpochMs"] as? Number)?.toLong() == 0L) {
                                row["scheduledDepartureEpochMs"] = row["scheduledAlarmEpochMs"]
                            }
                        }
                    }
                }
                return null
            }
        }

        val db = Proxy.newProxyInstance(
            SupportSQLiteDatabase::class.java.classLoader,
            arrayOf(SupportSQLiteDatabase::class.java),
            simulatedDbHandler
        ) as SupportSQLiteDatabase

        // Execute direct upgrade from 1 to 3
        AdaDatabase.MIGRATION_1_3.migrate(db)

        val alarm = v1Alarms["alarm-101"]!!
        // 1. Original fields survive intact
        assertEquals("alarm-101", alarm["id"])
        assertEquals("Morning Office Commute", alarm["title"])
        assertEquals("Tech Park", alarm["destinationName"])
        assertEquals(37.7749, alarm["destinationLat"])
        assertEquals(-122.4194, alarm["destinationLng"])
        assertEquals(1710000000000L, alarm["scheduledAlarmEpochMs"])

        // 2. V2 Sync fields added with correct defaults
        assertEquals("PENDING", alarm["syncStatus"])
        assertEquals(null, alarm["serverId"])

        // 3. V3 Journey tracking fields added and backfilled correctly
        assertEquals(1710000000000L, alarm["scheduledDepartureEpochMs"]) // Backfilled from scheduledAlarmEpochMs!
        assertEquals(15, alarm["trackingLeadMinutes"])
        assertEquals(1000, alarm["approachingThresholdMeters"])
        assertEquals(100, alarm["arrivalThresholdMeters"])
        assertEquals(0, alarm["isApproachingAlertSent"])
        assertEquals(0, alarm["isArrivalConfirmed"])
        assertEquals(0, alarm["isTrafficAware"])
        assertEquals("FALLBACK", alarm["etaSource"])

        // 4. Destinations table preserves original values and receives sync fields
        val dest = v1Destinations["dest-201"]!!
        assertEquals("dest-201", dest["id"])
        assertEquals("HQ Office", dest["name"])
        assertEquals(0, dest["isSynced"])
        assertEquals(null, dest["serverId"])
    }
}
