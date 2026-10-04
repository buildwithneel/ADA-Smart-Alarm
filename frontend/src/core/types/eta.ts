/**
 * ADA ETA Calculation Engine — Frontend Domain Types.
 *
 * These types mirror the backend ETACalculateResponse/ETAPreviewResponse
 * schemas and are the single source of truth for the frontend ETA layer.
 */

export type WeatherCondition =
  | "clear"
  | "cloudy"
  | "rain"
  | "heavy_rain"
  | "storm"
  | "snow"
  | "fog"
  | "unknown";

// ---------------------------------------------------------------------------
// Request types (sent to backend)
// ---------------------------------------------------------------------------

export interface ETACalculateRequest {
  origin_lat: number;
  origin_lng: number;
  dest_lat: number;
  dest_lng: number;
  desired_arrival_time: string; // "HH:MM" 24h format
  preparation_time_minutes?: number;
  safety_buffer_minutes?: number;
  transport_mode?: "driving" | "transit" | "bicycling" | "walking";
  // Optional: pass pre-computed route durations to skip backend routing call
  override_base_duration_seconds?: number;
  override_traffic_duration_seconds?: number;
  weather_condition?: WeatherCondition;
  target_date_iso?: string;
}

export interface ETAPreviewRequest {
  origin_lat: number;
  origin_lng: number;
  dest_lat: number;
  dest_lng: number;
  desired_arrival_time: string;
  preparation_time_minutes?: number;
  safety_buffer_minutes?: number;
  transport_mode?: "driving" | "transit" | "bicycling" | "walking";
  // If client has already computed route, pass these to skip server routing call
  base_duration_seconds?: number;
  traffic_duration_seconds?: number;
}

// ---------------------------------------------------------------------------
// Response types (received from backend)
// ---------------------------------------------------------------------------

export interface ETABreakdown {
  /** Route duration without traffic (minutes) */
  base_travel_minutes: number;
  /** Route duration with live traffic (minutes) */
  traffic_duration_minutes: number;
  /** Extra minutes due to traffic congestion */
  traffic_delay_minutes: number;
  /** Route distance in kilometres */
  distance_km: number | null;
  /** Explicit safety buffer applied */
  safety_buffer_minutes: number;
  /** Additional minutes due to adverse weather */
  weather_buffer_minutes: number;
  /** Total commute budget (travel + all buffers) */
  total_travel_with_buffer_minutes: number;
  /** Morning routine / preparation time */
  preparation_time_minutes: number;
  /** Weather condition label that triggered modifier */
  weather_condition: string | null;
  /** Which routing provider resolved the route */
  data_source: string;
  /** Confidence in the calculation [0.0 - 1.0] */
  confidence_score: number;
}

export interface ETACalculateResponse {
  /** Wake time in HH:MM 12h format (e.g. "07:30 AM") */
  recommended_wake_time: string;
  /** Leave home time in HH:MM 12h format */
  recommended_leave_time: string;
  /** Expected arrival time echoed back */
  expected_arrival_time: string;

  /** ISO-8601 datetime representations */
  wake_time_iso: string;
  leave_time_iso: string;
  arrival_time_iso: string;
  planned_arrival_time?: string;
  planned_arrival_time_iso?: string;

  /** Total travel time including traffic (minutes) */
  total_travel_minutes: number;
  /** Total time from wake to arrival (minutes) */
  total_time_budget_minutes: number;

  /** Detailed breakdown of all applied modifiers */
  breakdown: ETABreakdown;

  calculation_timestamp: string;
  engine_version: string;
}

export interface ETAPreviewResponse {
  recommended_wake_time: string;
  recommended_leave_time: string;
  expected_arrival_time: string;
  planned_arrival_time?: string;

  total_travel_minutes: number;
  traffic_delay_minutes: number;
  preparation_time_minutes: number;
  safety_buffer_minutes: number;
  total_budget_minutes: number;

  data_source: string;
  confidence_score: number;
}

export interface AlarmETAUpdateResult {
  alarm_id: string;
  calculated_wake_time: string | null;
  calculated_leave_time: string | null;
  current_travel_minutes: number;
  traffic_delay_minutes: number;
  last_evaluated_at: string;
  confidence_score: number;
}

// ---------------------------------------------------------------------------
// Computed display helpers  (derived types used in UI)
// ---------------------------------------------------------------------------

/**
 * Flattened display model for the live preview panel in CreateAlarmPage.
 * Mirrors the old inline preview state for backward compatibility.
 */
export interface ETALivePreview {
  wakeTime: string;
  leaveTime: string;
  arrivalTime: string;
  plannedArrivalTime?: string;
  travelMinutes: number;
  baseMinutes: number;
  trafficDelayMinutes: number;
  safetyBufferMinutes: number;
  weatherBufferMinutes: number;
  totalBudgetMinutes: number;
  distanceText: string;
  congestionLevel: string;
  provider: string;
  confidenceScore: number;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

export const DEFAULT_ETA_PREVIEW: ETALivePreview = {
  wakeTime: "--:-- --",
  leaveTime: "--:-- --",
  arrivalTime: "--:-- --",
  plannedArrivalTime: "--:-- --",
  travelMinutes: 0,
  baseMinutes: 0,
  trafficDelayMinutes: 0,
  safetyBufferMinutes: 15,
  weatherBufferMinutes: 0,
  totalBudgetMinutes: 0,
  distanceText: "—",
  congestionLevel: "unknown",
  provider: "—",
  confidenceScore: 0,
  isLoading: false,
  error: null,
  lastUpdated: null,
};
