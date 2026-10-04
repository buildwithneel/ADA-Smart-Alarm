export type WeatherCondition =
  | 'clear'
  | 'cloudy'
  | 'rain'
  | 'heavy_rain'
  | 'thunderstorm'
  | 'snow'
  | 'fog'
  | 'windy'
  | 'unknown';

export interface WeatherAlert {
  title: string;
  description: string;
  severity: 'info' | 'moderate' | 'severe' | 'extreme';
  valid_from: string;
  valid_until: string;
  source: string;
  official_url?: string | null;
}

export interface WeatherData {
  latitude: number;
  longitude: number;
  timestamp: string;
  valid_from: string;
  valid_until: string;
  temperature_c?: number | null;
  precipitation_probability?: number | null;
  precipitation_mm?: number | null;
  condition: WeatherCondition;
  condition_text: string;
  wind_speed_kmh?: number | null;
  is_severe: boolean;
  alerts: WeatherAlert[];
  provider: string;
  retrieved_at: string;
  attribution: string;
}

export type ContextType = 'weather' | 'calendar';
export type ContextRelevance = 'high' | 'medium' | 'low' | 'none';
export type ContextFinding =
  | 'CLEAR_CONDITIONS'
  | 'RAIN_DURING_JOURNEY'
  | 'SEVERE_WEATHER_ALERT'
  | 'CALENDAR_EVENT_TIME_CHANGED'
  | 'CALENDAR_EVENT_LOCATION_CHANGED'
  | 'CALENDAR_EVENT_CANCELLED'
  | 'CONTEXT_DATA_UNAVAILABLE';

export type ContextAction =
  | 'none'
  | 'warn_user'
  | 'apply_buffer'
  | 'reschedule_arrival'
  | 'cancel_alarm';

export interface ContextResult {
  context_type: ContextType;
  source: string;
  evaluated_at: string;
  valid_time_window: {
    start?: string | null;
    end?: string | null;
  };
  freshness: 'fresh' | 'stale' | 'expired';
  relevance: ContextRelevance;
  finding: ContextFinding;
  recommended_action: ContextAction;
  recommended_buffer_minutes: number;
  requires_confirmation: boolean;
  explanation: string;
  policy_version: string;
  metadata: Record<string, any>;
}

export interface ContextSummary {
  alarm_id: string;
  evaluated_at: string;
  results: ContextResult[];
  has_weather_warning: boolean;
  has_calendar_warning: boolean;
  recommended_total_buffer: number;
}
