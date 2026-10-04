/**
 * Centralized Design System Tokens for ADA.
 * Ensures consistent visual hierarchy, spacing, radius, and elevation across the entire application.
 */

export const tokens = {
  colors: {
    // Neutral foundations
    bgPrimaryDark: "#090d16",
    bgSecondaryDark: "#0f1626",
    bgSurfaceDark: "#151e33",
    bgBorderDark: "rgba(255, 255, 255, 0.08)",

    bgPrimaryLight: "#f8fafc",
    bgSecondaryLight: "#ffffff",
    bgSurfaceLight: "#f1f5f9",
    bgBorderLight: "rgba(0, 0, 0, 0.08)",

    // Brand Accent (Subtle, Linear-style indigo)
    brand: {
      50: "#eef2ff",
      100: "#e0e7ff",
      200: "#c7d2fe",
      300: "#a5b4fc",
      400: "#818cf8",
      500: "#6366f1",
      600: "#4f46e5",
      700: "#4338ca",
      800: "#3730a3",
      900: "#312e81",
    },

    // Semantic Status Colors
    semantic: {
      success: "#10b981", // On-time, Active
      warning: "#f59e0b", // Moderate traffic, Weather advisory
      error: "#ef4444",   // Severe delay, Alarm missed
      info: "#3b82f6",    // Informational notice
    },

    // Traffic congestion levels
    traffic: {
      low: "#10b981",      // Clear traffic
      moderate: "#f59e0b", // Minor slowdown (+5-10m)
      heavy: "#ef4444",    // Congested (+15m+)
      severe: "#b91c1c",   // Road closure / extreme delay
    },
  },

  typography: {
    fontSans: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontMono: '"JetBrains Mono", monospace',
    scale: {
      display: "text-4xl md:text-5xl font-black tracking-tight",
      h1: "text-2xl md:text-3xl font-extrabold tracking-tight",
      h2: "text-xl md:text-2xl font-bold tracking-tight",
      h3: "text-lg font-semibold tracking-tight",
      body: "text-sm leading-relaxed",
      small: "text-xs font-medium",
      caption: "text-[11px] font-medium tracking-wide",
    },
  },

  spacing: {
    xs: "0.25rem", // 4px
    sm: "0.5rem",  // 8px
    md: "1rem",    // 16px
    lg: "1.5rem",  // 24px
    xl: "2rem",    // 32px
    "2xl": "3rem", // 48px
  },

  radius: {
    sm: "0.5rem",   // 8px
    md: "0.75rem",  // 12px
    lg: "1rem",     // 16px
    xl: "1.25rem",  // 20px
    full: "9999px",
  },

  shadows: {
    subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    card: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)",
    floating: "0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.2)",
    accentGlow: "0 10px 30px -5px rgba(99, 102, 241, 0.25)",
  },

  transitions: {
    fast: "150ms cubic-bezier(0.16, 1, 0.3, 1)",
    normal: "250ms cubic-bezier(0.16, 1, 0.3, 1)",
    slow: "400ms cubic-bezier(0.16, 1, 0.3, 1)",
  },

  zIndex: {
    base: 0,
    card: 10,
    sticky: 20,
    backdrop: 30,
    drawer: 40,
    modal: 50,
    toast: 60,
    tooltip: 70,
  },

  breakpoints: {
    mobileSmall: 320,
    mobileStandard: 375,
    mobileLarge: 430,
    tablet: 768,
    desktopSmall: 1024,
    desktopStandard: 1280,
    desktopWide: 1440,
  },
} as const;
