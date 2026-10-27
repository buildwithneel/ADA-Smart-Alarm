/**
 * ADA Mobile Journey Details & Live Tracking Screen.
 * Presents real-time telemetry, live ETA, traffic condition badge, and manual controls.
 */

import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { AlarmDto } from "@ada/shared";
import { AdaApiClient } from "../api/apiClient.js";
import { colors, spacing, typography } from "../theme/theme.js";

interface JourneyDetailScreenProps {
  journeyId: string;
  apiClient: AdaApiClient;
  onBack: () => void;
}

export const JourneyDetailScreen: React.FC<JourneyDetailScreenProps> = ({
  journeyId,
  apiClient,
  onBack,
}) => {
  const [alarm, setAlarm] = useState<AlarmDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchDetail = async () => {
    try {
      const data = await apiClient.getAlarm(journeyId);
      setAlarm(data);
    } catch {
      // Error handling
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    const interval = setInterval(fetchDetail, 10000); // 10s telemetry poll
    return () => clearInterval(interval);
  }, [journeyId]);

  const handleStartTracking = async () => {
    setIsUpdating(true);
    try {
      await apiClient.updateAlarm(journeyId, { status: "active_tracking" });
      fetchDetail();
    } finally {
      setIsUpdating(false);
    }
  };

  const handleStopTracking = async () => {
    setIsUpdating(true);
    try {
      await apiClient.updateAlarm(journeyId, { status: "scheduled" });
      fetchDetail();
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = () => {
    Alert.alert("Cancel Journey", "Are you sure you want to cancel this scheduled journey?", [
      { text: "No", style: "cancel" },
      {
        text: "Yes, Cancel",
        style: "destructive",
        onPress: async () => {
          await apiClient.deleteAlarm(journeyId);
          onBack();
        },
      },
    ]);
  };

  if (isLoading || !alarm) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  const isLiveTracking = alarm.status === "active_tracking";
  const isTrafficAware = (alarm.traffic_delay_minutes ?? 0) > 0;

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.statusBadge}>{alarm.status.toUpperCase()}</Text>
      </View>

      <Text style={typography.titleLarge}>{alarm.title}</Text>
      <Text style={[typography.caption, { marginTop: 4, marginBottom: spacing.md }]}>
        Target Arrival: {alarm.arrival_time}
      </Text>

      {/* Primary ETA Spotlight */}
      <View style={styles.etaCard}>
        <Text style={styles.etaLabel}>PREDICTED ARRIVAL (DYNAMIC ETA)</Text>
        <Text style={styles.etaTime}>{alarm.planned_arrival_time ?? alarm.arrival_time}</Text>

        <View style={styles.trafficBadgeContainer}>
          <Text
            style={[
              styles.trafficBadge,
              { backgroundColor: isTrafficAware ? colors.badgeTraffic : colors.badgeFallback },
            ]}
          >
            {isTrafficAware ? "Live Road Traffic" : "Fallback Estimate"}
          </Text>
        </View>

        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>Travel Time</Text>
            <Text style={styles.statValue}>{alarm.current_travel_minutes ?? 0}m</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>Traffic Delay</Text>
            <Text style={styles.statValue}>+{alarm.traffic_delay_minutes ?? 0}m</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statLabel}>Safety Buffer</Text>
            <Text style={styles.statValue}>{alarm.safety_buffer}m</Text>
          </View>
        </View>
      </View>

      {/* Schedule Milestones */}
      <View style={styles.milestonesCard}>
        <Text style={[typography.titleMedium, { marginBottom: spacing.md }]}>Schedule Milestones</Text>
        <View style={styles.milestoneRow}>
          <Text style={typography.bodyMedium}>Recommended Wake-up</Text>
          <Text style={typography.bodyLarge}>{alarm.calculated_wake_time ?? "--:--"}</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.milestoneRow}>
          <Text style={typography.bodyMedium}>Recommended Departure</Text>
          <Text style={typography.bodyLarge}>{alarm.calculated_leave_time ?? "--:--"}</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.milestoneRow}>
          <Text style={typography.bodyMedium}>Morning Routine Buffer</Text>
          <Text style={typography.bodyLarge}>{alarm.preparation_time} min</Text>
        </View>
      </View>

      {/* Action Controls */}
      <View style={styles.actionsContainer}>
        {isLiveTracking ? (
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: colors.accent }]}
            onPress={handleStopTracking}
            disabled={isUpdating}
          >
            <Text style={styles.actionButtonText}>Stop Active Tracking</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: colors.primary }]}
            onPress={handleStartTracking}
            disabled={isUpdating}
          >
            <Text style={styles.actionButtonText}>Start Journey Tracking Now</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={[styles.actionButton, { backgroundColor: "transparent", borderWidth: 1, borderColor: colors.danger }]}
          onPress={handleDelete}
        >
          <Text style={[styles.actionButtonText, { color: colors.danger }]}>Cancel Journey</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.xl,
  },
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  backButton: {
    paddingVertical: spacing.xs,
  },
  backButtonText: {
    color: colors.primaryLight,
    fontSize: 16,
    fontWeight: "600",
  },
  statusBadge: {
    ...typography.badge,
    backgroundColor: colors.surfaceHighlight,
    color: colors.textPrimary,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  etaCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.primaryContainer,
    marginBottom: spacing.lg,
  },
  etaLabel: {
    ...typography.caption,
    letterSpacing: 1,
  },
  etaTime: {
    fontSize: 32,
    fontWeight: "800",
    color: colors.textPrimary,
    marginVertical: spacing.xs,
  },
  trafficBadgeContainer: {
    flexDirection: "row",
    marginBottom: spacing.md,
  },
  trafficBadge: {
    ...typography.badge,
    color: "#FFFFFF",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  statsGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: colors.surfaceHighlight,
    borderRadius: 8,
    padding: spacing.sm,
  },
  statBox: {
    alignItems: "center",
  },
  statLabel: {
    ...typography.caption,
  },
  statValue: {
    ...typography.bodyLarge,
    fontWeight: "700",
  },
  milestonesCard: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  milestoneRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: spacing.sm,
  },
  actionsContainer: {
    marginBottom: spacing.xxl,
  },
  actionButton: {
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  actionButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 15,
  },
});
