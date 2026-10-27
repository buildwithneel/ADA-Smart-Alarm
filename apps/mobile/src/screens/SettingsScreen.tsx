/**
 * ADA Mobile Settings Screen.
 * Preferences, default alarm buffers, timezone, and account management.
 */

import React from "react";
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { TokenStorage } from "../auth/tokenStorage.js";
import { colors, spacing, typography } from "../theme/theme.js";

interface SettingsScreenProps {
  onBack: () => void;
  onSignOut: () => void;
}

export const SettingsScreen: React.FC<SettingsScreenProps> = ({ onBack, onSignOut }) => {
  const handleSignOut = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await TokenStorage.clearAll();
          onSignOut();
        },
      },
    ]);
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>← Back</Text>
        </TouchableOpacity>
        <Text style={typography.titleMedium}>Settings</Text>
      </View>

      {/* Account Section */}
      <View style={styles.section}>
        <Text style={styles.sectionHeader}>ACCOUNT & PROFILE</Text>
        <View style={styles.row}>
          <Text style={typography.bodyLarge}>User Account</Text>
          <Text style={typography.bodyMedium}>Signed In</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.row}>
          <Text style={typography.bodyLarge}>Timezone</Text>
          <Text style={typography.bodyMedium}>Asia/Kolkata</Text>
        </View>
      </View>

      {/* Commute Defaults */}
      <View style={styles.section}>
        <Text style={styles.sectionHeader}>COMMUTE DEFAULTS</Text>
        <View style={styles.row}>
          <Text style={typography.bodyLarge}>Default Preparation</Text>
          <Text style={typography.bodyMedium}>30 mins</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.row}>
          <Text style={typography.bodyLarge}>Default Safety Buffer</Text>
          <Text style={typography.bodyMedium}>15 mins</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.row}>
          <Text style={typography.bodyLarge}>Tracking Lead Time</Text>
          <Text style={typography.bodyMedium}>15 mins before</Text>
        </View>
      </View>

      {/* Build Info */}
      <View style={styles.section}>
        <Text style={styles.sectionHeader}>BUILD & CAPABILITIES</Text>
        <View style={styles.row}>
          <Text style={typography.bodyLarge}>App Version</Text>
          <Text style={typography.bodyMedium}>1.0.0 (Expo Dev)</Text>
        </View>
        <View style={styles.divider} />
        <View style={styles.row}>
          <Text style={typography.bodyLarge}>Bundle Identifier</Text>
          <Text style={typography.caption}>com.thinkx.ada.mobile</Text>
        </View>
      </View>

      {/* Sign Out Button */}
      <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut}>
        <Text style={styles.signOutButtonText}>Sign Out of ADA</Text>
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
  section: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  sectionHeader: {
    ...typography.caption,
    letterSpacing: 0.5,
    marginBottom: spacing.sm,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: spacing.xs,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
    marginVertical: spacing.sm,
  },
  signOutButton: {
    borderColor: colors.danger,
    borderWidth: 1,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: spacing.xxl,
  },
  signOutButtonText: {
    color: colors.danger,
    fontWeight: "700",
    fontSize: 15,
  },
});
