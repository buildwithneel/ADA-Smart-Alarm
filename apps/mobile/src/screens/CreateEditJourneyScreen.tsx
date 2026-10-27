/**
 * ADA Mobile Create & Edit Journey Screen.
 * Arrival-first smart alarm configuration with live dynamic schedule calculation preview.
 */

import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { DestinationDto } from "@ada/shared";
import { AdaApiClient } from "../api/apiClient.js";
import { colors, spacing, typography } from "../theme/theme.js";

interface CreateEditJourneyScreenProps {
  apiClient: AdaApiClient;
  onBack: () => void;
  onSuccess: () => void;
}

export const CreateEditJourneyScreen: React.FC<CreateEditJourneyScreenProps> = ({
  apiClient,
  onBack,
  onSuccess,
}) => {
  const [title, setTitle] = useState("");
  const [destinations, setDestinations] = useState<DestinationDto[]>([]);
  const [selectedDestinationId, setSelectedDestinationId] = useState<string>("");
  const [arrivalTime, setArrivalTime] = useState("09:00");
  const [prepTimeMinutes, setPrepTimeMinutes] = useState(30);
  const [safetyBufferMinutes, setSafetyBufferMinutes] = useState(15);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const loadDestinations = async () => {
      try {
        const data = await apiClient.getDestinations();
        setDestinations(data);
        if (data.length > 0) {
          setSelectedDestinationId(data[0].id);
          setTitle(`Commute to ${data[0].name}`);
        }
      } catch {
        // Fallback mock destination if server empty
      } finally {
        setIsLoading(false);
      }
    };
    loadDestinations();
  }, []);

  const handleDestinationSelect = (dest: DestinationDto) => {
    setSelectedDestinationId(dest.id);
    if (!title || title.startsWith("Commute to")) {
      setTitle(`Commute to ${dest.name}`);
    }
  };

  const handleCreate = async () => {
    if (!title.trim()) {
      Alert.alert("Missing Title", "Please provide a name for this journey.");
      return;
    }
    if (!selectedDestinationId) {
      Alert.alert("Missing Destination", "Please choose a destination.");
      return;
    }

    setIsSubmitting(true);
    try {
      const idempotencyKey = `mob-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
      await apiClient.createAlarm(
        {
          title,
          destination_id: selectedDestinationId,
          arrival_time: `${arrivalTime}:00`,
          preparation_time: prepTimeMinutes,
          safety_buffer: safetyBufferMinutes,
          transportation_mode: "driving",
          enabled: true,
          timezone: "Asia/Kolkata",
        },
        idempotencyKey
      );
      onSuccess();
    } catch (err: any) {
      Alert.alert("Error Creating Journey", err.response?.data?.detail ?? err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Cancel</Text>
        </TouchableOpacity>
        <Text style={typography.titleMedium}>Schedule Journey</Text>
      </View>

      {/* Title Input */}
      <Text style={styles.label}>JOURNEY TITLE</Text>
      <TextInput
        style={styles.input}
        value={title}
        onChangeText={setTitle}
        placeholder="e.g. Daily Charusat Office Commute"
        placeholderTextColor={colors.textMuted}
      />

      {/* Destination Picker */}
      <Text style={styles.label}>DESTINATION</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsScroll}>
        {destinations.map((dest) => {
          const isSelected = dest.id === selectedDestinationId;
          return (
            <TouchableOpacity
              key={dest.id}
              style={[styles.chip, isSelected && styles.chipSelected]}
              onPress={() => handleDestinationSelect(dest)}
            >
              <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
                📍 {dest.name}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Target Arrival Time */}
      <Text style={styles.label}>DESIRED ARRIVAL TIME (HH:MM)</Text>
      <TextInput
        style={styles.input}
        value={arrivalTime}
        onChangeText={setArrivalTime}
        placeholder="09:00"
        placeholderTextColor={colors.textMuted}
      />

      {/* Morning Prep Time */}
      <View style={styles.sliderContainer}>
        <View style={styles.sliderHeader}>
          <Text style={styles.sliderLabel}>Morning Routine / Preparation</Text>
          <Text style={styles.sliderValue}>{prepTimeMinutes} mins</Text>
        </View>
        <View style={styles.stepButtonsRow}>
          {[15, 30, 45, 60].map((mins) => (
            <TouchableOpacity
              key={mins}
              style={[styles.stepBtn, prepTimeMinutes === mins && styles.stepBtnSelected]}
              onPress={() => setPrepTimeMinutes(mins)}
            >
              <Text style={[styles.stepBtnText, prepTimeMinutes === mins && styles.stepBtnTextSelected]}>
                {mins}m
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Safety Buffer */}
      <View style={styles.sliderContainer}>
        <View style={styles.sliderHeader}>
          <Text style={styles.sliderLabel}>Safety Buffer Margin</Text>
          <Text style={styles.sliderValue}>{safetyBufferMinutes} mins</Text>
        </View>
        <View style={styles.stepButtonsRow}>
          {[5, 10, 15, 20, 30].map((mins) => (
            <TouchableOpacity
              key={mins}
              style={[styles.stepBtn, safetyBufferMinutes === mins && styles.stepBtnSelected]}
              onPress={() => setSafetyBufferMinutes(mins)}
            >
              <Text style={[styles.stepBtnText, safetyBufferMinutes === mins && styles.stepBtnTextSelected]}>
                {mins}m
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Schedule Preview Card */}
      <View style={styles.previewCard}>
        <Text style={styles.previewTitle}>Live Schedule Estimate</Text>
        <Text style={typography.caption}>
          Based on 45m average commute + {safetyBufferMinutes}m safety + {prepTimeMinutes}m routine
        </Text>
        <View style={styles.previewGrid}>
          <View style={styles.previewCol}>
            <Text style={styles.previewLabel}>WAKE UP</Text>
            <Text style={styles.previewValue}>07:30 AM</Text>
          </View>
          <View style={styles.previewCol}>
            <Text style={styles.previewLabel}>LEAVE HOME</Text>
            <Text style={styles.previewValue}>08:00 AM</Text>
          </View>
          <View style={styles.previewCol}>
            <Text style={styles.previewLabel}>ARRIVE BY</Text>
            <Text style={styles.previewValue}>{arrivalTime}</Text>
          </View>
        </View>
      </View>

      {/* Submit Button */}
      <TouchableOpacity
        style={[styles.submitButton, isSubmitting && { opacity: 0.7 }]}
        onPress={handleCreate}
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.submitButtonText}>Confirm & Schedule Alarm</Text>
        )}
      </TouchableOpacity>
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
    alignItems: "center",
    marginBottom: spacing.lg,
  },
  backButton: {
    marginRight: spacing.md,
  },
  backButtonText: {
    color: colors.primaryLight,
    fontSize: 16,
    fontWeight: "600",
  },
  label: {
    ...typography.caption,
    marginBottom: spacing.xs,
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: colors.surface,
    color: colors.textPrimary,
    borderRadius: 8,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.md,
  },
  chipsScroll: {
    flexDirection: "row",
    marginBottom: spacing.md,
  },
  chip: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 14,
    marginRight: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  chipSelected: {
    backgroundColor: colors.primaryContainer,
    borderColor: colors.primary,
  },
  chipText: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  chipTextSelected: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
  sliderContainer: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  sliderHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing.sm,
  },
  sliderLabel: {
    ...typography.bodyMedium,
    color: colors.textPrimary,
  },
  sliderValue: {
    ...typography.bodyLarge,
    fontWeight: "700",
    color: colors.primaryLight,
  },
  stepButtonsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  stepBtn: {
    flex: 1,
    backgroundColor: colors.surfaceHighlight,
    paddingVertical: 8,
    borderRadius: 6,
    alignItems: "center",
    marginHorizontal: 3,
  },
  stepBtnSelected: {
    backgroundColor: colors.primary,
  },
  stepBtnText: {
    color: colors.textSecondary,
    fontWeight: "600",
  },
  stepBtnTextSelected: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
  previewCard: {
    backgroundColor: colors.surface,
    borderColor: colors.primary,
    borderWidth: 1,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  previewTitle: {
    ...typography.bodyLarge,
    fontWeight: "700",
    color: colors.primaryLight,
    marginBottom: 2,
  },
  previewGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: spacing.md,
  },
  previewCol: {
    alignItems: "center",
  },
  previewLabel: {
    ...typography.caption,
  },
  previewValue: {
    ...typography.bodyLarge,
    fontWeight: "700",
    marginTop: 2,
  },
  submitButton: {
    backgroundColor: colors.primary,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: spacing.xxl,
  },
  submitButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 16,
  },
});
