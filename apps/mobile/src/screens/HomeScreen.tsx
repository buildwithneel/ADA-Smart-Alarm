/**
 * ADA Mobile Home Screen.
 * Displays Active Journey spotlight card with dynamic countdown, upcoming journeys list,
 * quick toggle controls, and permission diagnostics shortcuts.
 */

import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Switch,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { AlarmDto } from "@ada/shared";
import { AdaApiClient } from "../api/apiClient.js";
import { colors, spacing, typography } from "../theme/theme.js";

interface HomeScreenProps {
  apiClient: AdaApiClient;
  onNavigateToJourney: (journeyId: string) => void;
  onNavigateToCreate: () => void;
  onNavigateToDiagnostics: () => void;
  onNavigateToSettings: () => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  apiClient,
  onNavigateToJourney,
  onNavigateToCreate,
  onNavigateToDiagnostics,
  onNavigateToSettings,
}) => {
  const [alarms, setAlarms] = useState<AlarmDto[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchAlarms = async () => {
    try {
      setErrorMessage(null);
      const data = await apiClient.getAlarms();
      setAlarms(data);
    } catch (err: any) {
      setErrorMessage("Unable to connect to ADA server. Check your network or offline status.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAlarms();
  }, []);

  const handleToggle = async (alarm: AlarmDto) => {
    try {
      if (alarm.enabled) {
        await apiClient.disableAlarm(alarm.id);
      } else {
        await apiClient.enableAlarm(alarm.id);
      }
      fetchAlarms();
    } catch {
      // Revert or show toast
    }
  };

  const activeAlarm = alarms.find((a) => a.enabled && a.status === "active_tracking") || alarms.find((a) => a.enabled);

  return (
    <View style={styles.container}>
      {/* Top Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>ADA Smart Alarm</Text>
          <Text style={styles.subtitle}>Destination-Aware Commute</Text>
        </View>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={onNavigateToDiagnostics} style={styles.iconButton}>
            <Text style={styles.iconText}>⚙️</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Error / Offline Banner */}
      {errorMessage && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{errorMessage}</Text>
        </View>
      )}

      {/* Main Content */}
      {isLoading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[typography.bodyMedium, { marginTop: spacing.md }]}>Loading journeys...</Text>
        </View>
      ) : (
        <FlatList
          data={alarms}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={() => { setIsRefreshing(true); fetchAlarms(); }} />}
          ListHeaderComponent={
            <>
              {/* Spotlight Card */}
              {activeAlarm ? (
                <TouchableOpacity
                  style={styles.spotlightCard}
                  onPress={() => onNavigateToJourney(activeAlarm.id)}
                  activeOpacity={0.8}
                >
                  <View style={styles.cardHeader}>
                    <Text style={styles.spotlightBadge}>
                      {activeAlarm.status === "active_tracking" ? "🟢 LIVE TRACKING" : "NEXT JOURNEY"}
                    </Text>
                    <Switch
                      value={activeAlarm.enabled}
                      onValueChange={() => handleToggle(activeAlarm)}
                      trackColor={{ false: colors.surfaceHighlight, true: colors.primary }}
                    />
                  </View>
                  <Text style={styles.spotlightTitle}>{activeAlarm.title}</Text>
                  <Text style={styles.spotlightArrival}>Arrival: {activeAlarm.arrival_time}</Text>
                  <View style={styles.telemetryRow}>
                    <Text style={styles.telemetryItem}>Wake: {activeAlarm.calculated_wake_time ?? "--:--"}</Text>
                    <Text style={styles.telemetryItem}>Leave: {activeAlarm.calculated_leave_time ?? "--:--"}</Text>
                  </View>
                </TouchableOpacity>
              ) : (
                <View style={styles.emptyCard}>
                  <Text style={[typography.titleMedium, { color: colors.textSecondary }]}>No upcoming journeys</Text>
                  <Text style={[typography.bodyMedium, { textAlign: "center", marginTop: spacing.xs }]}>
                    Schedule a journey to have ADA monitor your commute and wake you at the right time.
                  </Text>
                </View>
              )}

              <Text style={[typography.titleMedium, styles.sectionHeader]}>All Scheduled Journeys</Text>
            </>
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.journeyItem}
              onPress={() => onNavigateToJourney(item.id)}
              activeOpacity={0.7}
            >
              <View style={{ flex: 1 }}>
                <Text style={typography.bodyLarge}>{item.title}</Text>
                <Text style={typography.caption}>Target Arrival: {item.arrival_time}</Text>
              </View>
              <Switch
                value={item.enabled}
                onValueChange={() => handleToggle(item)}
                trackColor={{ false: colors.surfaceHighlight, true: colors.primary }}
              />
            </TouchableOpacity>
          )}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={typography.bodyMedium}>No journeys configured yet.</Text>
            </View>
          }
          contentContainerStyle={{ paddingBottom: 100 }}
        />
      )}

      {/* Floating Action Button */}
      <TouchableOpacity style={styles.fab} onPress={onNavigateToCreate} activeOpacity={0.85}>
        <Text style={styles.fabText}>+ New Journey</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.xl,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  title: {
    ...typography.titleLarge,
  },
  subtitle: {
    ...typography.caption,
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
  },
  iconButton: {
    padding: spacing.sm,
    backgroundColor: colors.surface,
    borderRadius: 8,
  },
  iconText: {
    fontSize: 18,
  },
  errorBanner: {
    backgroundColor: "rgba(239, 68, 68, 0.2)",
    borderColor: colors.danger,
    borderWidth: 1,
    borderRadius: 8,
    padding: spacing.sm,
    marginBottom: spacing.md,
  },
  errorText: {
    color: colors.danger,
    fontSize: 13,
  },
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  spotlightCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.primaryContainer,
    marginBottom: spacing.lg,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  spotlightBadge: {
    ...typography.badge,
    color: colors.primaryLight,
  },
  spotlightTitle: {
    ...typography.titleLarge,
    marginBottom: spacing.xs,
  },
  spotlightArrival: {
    ...typography.bodyLarge,
    color: colors.textSecondary,
    marginBottom: spacing.md,
  },
  telemetryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: colors.surfaceHighlight,
    borderRadius: 8,
    padding: spacing.sm,
  },
  telemetryItem: {
    ...typography.caption,
    color: colors.textPrimary,
  },
  emptyCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.xl,
    alignItems: "center",
    marginBottom: spacing.lg,
  },
  sectionHeader: {
    marginBottom: spacing.sm,
  },
  journeyItem: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    flexDirection: "row",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  emptyContainer: {
    padding: spacing.xl,
    alignItems: "center",
  },
  fab: {
    position: "absolute",
    bottom: 24,
    right: 20,
    backgroundColor: colors.primary,
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 30,
    elevation: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  fabText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 15,
  },
});
