/**
 * ADA Mobile Calm & Focused Design System Tokens.
 * Harmonious slate & sapphire palette matching Jetpack Compose Material 3 implementation.
 */

export const colors = {
  background: "#0F172A", // Deep Slate
  surface: "#1E293B",    // Slate Card
  surfaceHighlight: "#334155",
  primary: "#3B82F6",    // Focused Cobalt / Sapphire
  primaryLight: "#60A5FA",
  primaryContainer: "#1E3A8A",
  secondary: "#10B981",  // Mint Green (Arrived / Success)
  accent: "#F59E0B",     // Amber / Warning / Recalculating
  danger: "#EF4444",     // Red / Error / Deviated
  textPrimary: "#F8FAFC",
  textSecondary: "#94A3B8",
  textMuted: "#64748B",
  border: "#334155",
  badgeTraffic: "#0EA5E9",
  badgeFallback: "#F97316",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const typography = {
  titleLarge: { fontSize: 24, fontWeight: "700" as const, color: colors.textPrimary },
  titleMedium: { fontSize: 20, fontWeight: "600" as const, color: colors.textPrimary },
  bodyLarge: { fontSize: 16, fontWeight: "400" as const, color: colors.textPrimary },
  bodyMedium: { fontSize: 14, fontWeight: "400" as const, color: colors.textSecondary },
  caption: { fontSize: 12, fontWeight: "500" as const, color: colors.textMuted },
  badge: { fontSize: 11, fontWeight: "700" as const, textTransform: "uppercase" as const },
};
