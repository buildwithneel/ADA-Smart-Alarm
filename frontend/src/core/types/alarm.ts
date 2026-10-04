export type TransportMode = "driving" | "transit" | "bicycling" | "walking";

export type AlarmStatus =
  | "draft"
  | "scheduled"
  | "active"
  | "calculating"
  | "ringing"
  | "dismissed"
  | "disabled"
  | "expired"
  | "completed"
  | "cancelled"
  | "urgent_schedule_change"
  | "missed_recalculation"
  | "error";

export interface AlarmScheduleChange {
  id: string;
  alarm_id: string | number;
  previous_wake_time?: string | null;
  new_wake_time: string;
  previous_leave_time?: string | null;
  new_leave_time: string;
  previous_planned_arrival?: string | null;
  new_planned_arrival: string;
  previous_travel_minutes?: number | null;
  new_travel_minutes: number;
  reason: string;
  schedule_version: number;
  created_at: string;
}

export interface Alarm {
  id: number;
  user_id: number;
  title: string;
  destination_name: string;
  destination_lat: number;
  destination_lng: number;
  origin_name?: string | null;
  origin_lat?: number | null;
  origin_lng?: number | null;
  use_live_gps: boolean;
  desired_arrival_time: string; // "HH:MM:SS" or "HH:MM"
  planned_arrival_time?: string | null;
  repeat_days: string;
  transport_mode: TransportMode;
  routine_minutes: number;
  buffer_minutes: number;
  current_travel_minutes: number;
  traffic_delay_minutes: number;
  calculated_leave_time?: string | null;
  calculated_wake_time?: string | null;
  weather_condition?: string | null;
  weather_temp_c?: number | null;
  last_evaluated_at?: string | null;
  last_calculated_at?: string | null;
  calculation_version?: string | null;
  timezone?: string | null;
  status: AlarmStatus;
  is_active: boolean;
  // Step 8: Dynamic Recalculation & History
  schedule_version?: number;
  last_route_refresh_at?: string | null;
  last_schedule_change_at?: string | null;
  schedule_change_reason?: string | null;
  route_freshness_state?: string;
  schedule_changes?: AlarmScheduleChange[];
  // Step 10: Weather + Calendar Context
  weather_buffer_minutes?: number | null;
  weather_condition_snapshot?: string | null;
  calendar_event_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlarmCreateInput {
  title: string;
  destination_name: string;
  destination_lat: number;
  destination_lng: number;
  origin_name?: string;
  origin_lat?: number;
  origin_lng?: number;
  use_live_gps: boolean;
  desired_arrival_time: string;
  repeat_days?: string;
  transport_mode: TransportMode;
  routine_minutes: number;
  buffer_minutes: number;
}

export interface AlarmCalculationPreview {
  travel_minutes: number;
  traffic_delay_minutes: number;
  recommended_leave_time: string;
  recommended_wake_time: string;
  weather_summary: string;
  confidence_score: number;
}
