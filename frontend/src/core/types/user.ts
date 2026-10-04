export interface User {
  id: number;
  firebase_uid: string;
  email: string;
  display_name?: string | null;
  avatar_url?: string | null;
  fcm_token?: string | null;
  is_active: boolean;
  default_routine_minutes: number;
  default_buffer_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface UserPreferences {
  theme: "dark" | "light" | "system";
  soundEnabled: boolean;
  vibrationEnabled: boolean;
  weatherAlerts: boolean;
  trafficThresholdMinutes: number;
}
