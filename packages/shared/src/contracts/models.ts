/**
 * ADA Shared API Contracts & Domain Models.
 * Strictly mirrors FastAPI schemas (`backend/app/schemas/`) and Kotlin DTOs (`android/app/src/main/kotlin/com/thinkx/ada/network/dto/NetworkDtos.kt`).
 */

export interface UserDto {
  id: string;
  firebaseUid?: string | null;
  email: string;
  name?: string | null;
  profileImage?: string | null;
  timezone?: string;
}

export interface DestinationDto {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  type?: string;
  is_favorite?: boolean;
}

export interface DestinationCreateDto {
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  type?: string;
  is_favorite?: boolean;
}

export interface AlarmDto {
  id: string;
  user_id?: string | null;
  destination_id: string;
  title: string;
  arrival_time: string; // ISO-8601 or HH:MM:SS
  preparation_time: number;
  safety_buffer: number;
  transportation_mode: string;
  enabled: boolean;
  status: string;
  timezone: string;
  calculated_wake_time?: string | null;
  calculated_leave_time?: string | null;
  planned_arrival_time?: string | null;
  current_travel_minutes?: number | null;
  traffic_delay_minutes?: number | null;
  schedule_version?: number;
  origin_lat?: number | null;
  origin_lng?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AlarmCreateDto {
  title: string;
  destination_id: string;
  arrival_time: string;
  arrival_date?: string | null;
  preparation_time?: number;
  safety_buffer?: number;
  transportation_mode?: string;
  enabled?: boolean;
  timezone?: string;
  origin_lat?: number | null;
  origin_lng?: number | null;
}

export interface AlarmUpdateDto {
  title?: string | null;
  destination_id?: string | null;
  arrival_time?: string | null;
  arrival_date?: string | null;
  preparation_time?: number | null;
  safety_buffer?: number | null;
  transportation_mode?: string | null;
  enabled?: boolean | null;
  status?: string | null;
  timezone?: string | null;
}

export interface LocationDto {
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  altitude?: number | null;
  heading?: number | null;
  speed?: number | null;
  timestamp?: number | null;
}

export interface RouteRequestDto {
  origin: LocationDto;
  destination: LocationDto;
  travel_mode?: string;
  departure_time?: number | null;
}

export interface RouteSummaryDto {
  formatted_distance?: string | null;
  formatted_duration?: string | null;
  formatted_traffic_delay?: string | null;
  congestion_level?: string | null;
}

export interface RouteResultDto {
  origin: { latitude?: number; longitude?: number } | Record<string, number>;
  destination: { latitude?: number; longitude?: number } | Record<string, number>;
  distance_meters: number;
  duration_seconds: number;
  traffic_duration_seconds: number;
  route_geometry: string;
  provider: string;
  is_traffic_aware: boolean;
  timestamp?: string;
  travel_mode?: string;
  summary?: RouteSummaryDto | null;
}

export enum EtaSource {
  TRAFFIC_AWARE_PROVIDER = "TRAFFIC_AWARE_PROVIDER",
  NON_TRAFFIC_FALLBACK = "NON_TRAFFIC_FALLBACK",
  CACHED_ESTIMATE = "CACHED_ESTIMATE",
}

export enum JourneyState {
  SCHEDULED = "SCHEDULED",
  READY_TO_TRACK = "READY_TO_TRACK",
  ACTIVE_TRACKING = "ACTIVE_TRACKING",
  RECALCULATING = "RECALCULATING",
  APPROACHING = "APPROACHING",
  ARRIVED = "ARRIVED",
  TRACKING_DEGRADED = "TRACKING_DEGRADED",
  CANCELLED = "CANCELLED",
  FAILED = "FAILED",
}

export enum JourneyAlertEvent {
  TRACKING_STARTED = "TRACKING_STARTED",
  APPROACHING_ALERT = "APPROACHING_ALERT",
  ARRIVAL_CONFIRMED = "ARRIVAL_CONFIRMED",
  ROUTE_DEVIATED = "ROUTE_DEVIATED",
  TRACKING_DEGRADED = "TRACKING_DEGRADED",
}

export interface JourneyLocationFix {
  latitude: number;
  longitude: number;
  accuracyMeters: number;
  timestampEpochMs: number;
  speedMps?: number | null;
  bearingDegrees?: number | null;
}

export interface DynamicEtaResult {
  predictedArrivalEpochMs: number;
  remainingDurationSeconds: number;
  remainingDistanceMeters: number;
  isTrafficAware: boolean;
  source: EtaSource;
  providerName: string;
  lastRefreshEpochMs: number;
  isStale: boolean;
  routeGeometry?: string;
}
