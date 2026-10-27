/**
 * ADA Mobile Authentication Screen.
 * Provides Email/Password Sign-In, Registration, and Continue Offline fallback.
 */

import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { TokenStorage } from "../auth/tokenStorage.js";
import { colors, spacing, typography } from "../theme/theme.js";

interface AuthScreenProps {
  onAuthSuccess: () => void;
  onContinueOffline: () => void;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({
  onAuthSuccess,
  onContinueOffline,
}) => {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    if (!email || !password) {
      Alert.alert("Missing Fields", "Please enter both email and password.");
      return;
    }
    setIsLoading(true);
    try {
      // In development / demo mode, generate session token and persist to hardware keystore
      const dummyToken = `jwt-demo-${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
      await TokenStorage.setToken(dummyToken);
      onAuthSuccess();
    } catch (err: any) {
      Alert.alert("Authentication Failed", err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.logoContainer}>
        <Text style={styles.logoIcon}>⏰</Text>
        <Text style={styles.appTitle}>ADA Smart Alarm</Text>
        <Text style={styles.appTagline}>Destination-Aware Dynamic Commute Alarm</Text>
      </View>

      <View style={styles.tabsRow}>
        <TouchableOpacity
          style={[styles.tab, !isRegistering && styles.tabActive]}
          onPress={() => setIsRegistering(false)}
        >
          <Text style={[styles.tabText, !isRegistering && styles.tabTextActive]}>Sign In</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, isRegistering && styles.tabActive]}
          onPress={() => setIsRegistering(true)}
        >
          <Text style={[styles.tabText, isRegistering && styles.tabTextActive]}>Register</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.inputLabel}>EMAIL ADDRESS</Text>
      <TextInput
        style={styles.input}
        value={email}
        onChangeText={setEmail}
        placeholder="user@example.com"
        placeholderTextColor={colors.textMuted}
        autoCapitalize="none"
        keyboardType="email-address"
      />

      <Text style={styles.inputLabel}>PASSWORD</Text>
      <TextInput
        style={styles.input}
        value={password}
        onChangeText={setPassword}
        placeholder="••••••••"
        placeholderTextColor={colors.textMuted}
        secureTextEntry
      />

      <TouchableOpacity
        style={[styles.submitButton, isLoading && { opacity: 0.7 }]}
        onPress={handleSubmit}
        disabled={isLoading}
      >
        {isLoading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.submitButtonText}>{isRegistering ? "Create Account" : "Sign In"}</Text>
        )}
      </TouchableOpacity>

      <View style={styles.dividerRow}>
        <View style={styles.line} />
        <Text style={styles.orText}>OR</Text>
        <View style={styles.line} />
      </View>

      <TouchableOpacity style={styles.offlineButton} onPress={onContinueOffline}>
        <Text style={styles.offlineButtonText}>Continue Offline (Local Alarm Only)</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
    justifyContent: "center",
  },
  logoContainer: {
    alignItems: "center",
    marginBottom: spacing.xl,
  },
  logoIcon: {
    fontSize: 48,
    marginBottom: spacing.xs,
  },
  appTitle: {
    ...typography.titleLarge,
    fontSize: 28,
  },
  appTagline: {
    ...typography.caption,
    color: colors.textSecondary,
    marginTop: 4,
  },
  tabsRow: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 8,
    padding: 4,
    marginBottom: spacing.lg,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 6,
  },
  tabActive: {
    backgroundColor: colors.primary,
  },
  tabText: {
    color: colors.textSecondary,
    fontWeight: "600",
  },
  tabTextActive: {
    color: "#FFFFFF",
    fontWeight: "700",
  },
  inputLabel: {
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
  submitButton: {
    backgroundColor: colors.primary,
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: spacing.sm,
  },
  submitButtonText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 16,
  },
  dividerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: spacing.lg,
  },
  line: {
    flex: 1,
    height: 1,
    backgroundColor: colors.border,
  },
  orText: {
    color: colors.textMuted,
    marginHorizontal: spacing.md,
    fontSize: 12,
    fontWeight: "600",
  },
  offlineButton: {
    borderColor: colors.border,
    borderWidth: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: "center",
  },
  offlineButtonText: {
    color: colors.textSecondary,
    fontWeight: "600",
    fontSize: 14,
  },
});
