import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User, UserPreferences } from "@/core/types/user";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  preferences: UserPreferences;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
  updatePreferences: (prefs: Partial<UserPreferences>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: {
        id: 1,
        firebase_uid: "dev-user-123",
        email: "alex@thinkx.ai",
        display_name: "Alex Vance",
        avatar_url: null,
        is_active: true,
        default_routine_minutes: 30,
        default_buffer_minutes: 15,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      token: "mock-jwt-token-for-dev",
      isAuthenticated: true,
      preferences: {
        theme: "dark",
        soundEnabled: true,
        vibrationEnabled: true,
        weatherAlerts: true,
        trafficThresholdMinutes: 10,
      },
      setAuth: (user, token) => set({ user, token, isAuthenticated: true }),
      clearAuth: () => set({ user: null, token: null, isAuthenticated: false }),
      updatePreferences: (prefs) =>
        set((state) => ({
          preferences: { ...state.preferences, ...prefs },
        })),
    }),
    {
      name: "ada-auth-storage",
    }
  )
);
