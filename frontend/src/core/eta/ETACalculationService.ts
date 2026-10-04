/**
 * ADA ETA Calculation Service — Frontend Pure Domain Layer.
 *
 * Mirrors the backend ETACalculationEngine for offline/instant calculations.
 * Used to compute optimistic previews while the API call is in-flight,
 * and as a deterministic fallback when the backend is unreachable.
 *
 * Design: Pure functions, no I/O, no side effects, fully testable.
 */

import type {
  ETACalculateResponse,
  ETALivePreview,
  ETAPreviewResponse,
  WeatherCondition,
} from "@/core/types/eta";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const ENGINE_VERSION = "1.0.0";

/** Heuristic travel speeds in km/h by transport mode */
const SPEED_KMH: Record<string, number> = {
  driving: 35,
  transit: 25,
  bicycling: 15,
  cycling: 15,
  walking: 4.5,
};

/** Weather buffer factors (% of traffic travel time added) */
const WEATHER_FACTORS: Partial<Record<WeatherCondition, number>> = {
  clear: 0,
  cloudy: 0,
  rain: 0.15,
  heavy_rain: 0.25,
  storm: 0.35,
  snow: 0.3,
  fog: 0.2,
  unknown: 0,
};

// ---------------------------------------------------------------------------
// Haversine distance (km)
// ---------------------------------------------------------------------------

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ---------------------------------------------------------------------------
// Heuristic route durations (seconds)
// ---------------------------------------------------------------------------

export function computeHeuristicDurations(
  originLat: number,
  originLng: number,
  destLat: number,
  destLng: number,
  transportMode: string
): { baseSecs: number; trafficSecs: number; distanceKm: number } {
  const distKm = haversineKm(originLat, originLng, destLat, destLng);
  const speedKmh = SPEED_KMH[transportMode.toLowerCase()] ?? 35;
  const baseSecs = Math.max(300, Math.round((distKm / speedKmh) * 3600));
  const trafficSecs =
    transportMode.toLowerCase() === "driving"
      ? Math.round(baseSecs * 1.2)
      : baseSecs;

  return { baseSecs, trafficSecs, distanceKm: distKm };
}

// ---------------------------------------------------------------------------
// Format helpers
// ---------------------------------------------------------------------------

export function format12h(date: Date): string {
  const h = date.getHours();
  const m = date.getMinutes();
  const period = h < 12 ? "AM" : "PM";
  const h12 = h % 12 || 12;
  return `${String(h12).padStart(2, "0")}:${String(m).padStart(2, "0")} ${period}`;
}

function parseArrivalToDate(arrivalTimeHHMM: string): Date {
  const [hStr, mStr] = arrivalTimeHHMM.split(":");
  const h = parseInt(hStr, 10);
  const m = parseInt(mStr, 10);

  const now = new Date();
  const candidate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0, 0);

  // If the requested time is more than 1 hour in the past, schedule for tomorrow
  if (candidate.getTime() < now.getTime() - 3600_000) {
    candidate.setDate(candidate.getDate() + 1);
  }

  return candidate;
}

// ---------------------------------------------------------------------------
// Core ETA computation (pure, no I/O)
// ---------------------------------------------------------------------------

export interface ETAComputeInput {
  desiredArrivalTime: string; // "HH:MM" 24h
  baseDurationSeconds: number;
  trafficDurationSeconds: number;
  preparationMinutes: number;
  safetyBufferMinutes: number;
  weatherCondition?: WeatherCondition;
  dataSource?: string;
  distanceKm?: number;
  confidenceScore?: number;
}

export interface ETAComputeResult {
  wakeTime: Date;
  leaveTime: Date;
  arrivalTime: Date;
  totalTravelMinutes: number;
  baseTravelMinutes: number;
  trafficDelayMinutes: number;
  safetyBufferMinutes: number;
  weatherBufferMinutes: number;
  totalBudgetMinutes: number;
  confidenceScore: number;
  dataSource: string;
  distanceKm: number | null;
}

export function computeETA(input: ETAComputeInput): ETAComputeResult {
  const {
    desiredArrivalTime,
    baseDurationSeconds,
    trafficDurationSeconds,
    preparationMinutes,
    safetyBufferMinutes,
    weatherCondition,
    dataSource = "heuristic",
    distanceKm,
    confidenceScore = 0.7,
  } = input;

  const arrivalTime = parseArrivalToDate(desiredArrivalTime);

  const baseTravelMins = Math.max(1, Math.round(baseDurationSeconds / 60));
  const trafficMins = Math.max(1, Math.round(trafficDurationSeconds / 60));
  const trafficDelayMins = Math.max(0, trafficMins - baseTravelMins);

  // Apply weather buffer
  const weatherFactor = weatherCondition
    ? (WEATHER_FACTORS[weatherCondition] ?? 0)
    : 0;
  const weatherBufferMins = Math.round(trafficMins * weatherFactor);

  const totalTravelWithBuffer = trafficMins + safetyBufferMinutes + weatherBufferMins;
  const totalBudget = totalTravelWithBuffer + preparationMinutes;

  const leaveTime = new Date(arrivalTime.getTime() - totalTravelWithBuffer * 60_000);
  const wakeTime = new Date(leaveTime.getTime() - preparationMinutes * 60_000);

  const adjustedConfidence =
    weatherBufferMins > 0 ? Math.max(0.5, confidenceScore - 0.05) : confidenceScore;

  return {
    wakeTime,
    leaveTime,
    arrivalTime,
    totalTravelMinutes: trafficMins,
    baseTravelMinutes: baseTravelMins,
    trafficDelayMinutes: trafficDelayMins,
    safetyBufferMinutes,
    weatherBufferMinutes: weatherBufferMins,
    totalBudgetMinutes: totalBudget,
    confidenceScore: Math.round(adjustedConfidence * 1000) / 1000,
    dataSource,
    distanceKm: distanceKm ?? null,
  };
}

// ---------------------------------------------------------------------------
// Build ETALivePreview display model from compute result
// ---------------------------------------------------------------------------

export function buildLivePreview(
  result: ETAComputeResult,
  distanceText: string,
  congestionLevel: string,
  isLoading = false,
  error: string | null = null
): ETALivePreview {
  return {
    wakeTime: format12h(result.wakeTime),
    leaveTime: format12h(result.leaveTime),
    arrivalTime: format12h(result.arrivalTime),
    plannedArrivalTime: format12h(
      new Date(result.arrivalTime.getTime() - result.safetyBufferMinutes * 60_000)
    ),
    travelMinutes: result.totalTravelMinutes,
    baseMinutes: result.baseTravelMinutes,
    trafficDelayMinutes: result.trafficDelayMinutes,
    safetyBufferMinutes: result.safetyBufferMinutes,
    weatherBufferMinutes: result.weatherBufferMinutes,
    totalBudgetMinutes: result.totalBudgetMinutes,
    distanceText,
    congestionLevel,
    provider: result.dataSource,
    confidenceScore: result.confidenceScore,
    isLoading,
    error,
    lastUpdated: new Date(),
  };
}

// ---------------------------------------------------------------------------
// Convert backend ETACalculateResponse → ETALivePreview (for display)
// ---------------------------------------------------------------------------

export function previewFromCalculateResponse(
  response: ETACalculateResponse,
  distanceText: string,
  congestionLevel: string
): ETALivePreview {
  return {
    wakeTime: response.recommended_wake_time,
    leaveTime: response.recommended_leave_time,
    arrivalTime: response.expected_arrival_time,
    plannedArrivalTime: response.planned_arrival_time,
    travelMinutes: response.total_travel_minutes,
    baseMinutes: response.breakdown.base_travel_minutes,
    trafficDelayMinutes: response.breakdown.traffic_delay_minutes,
    safetyBufferMinutes: response.breakdown.safety_buffer_minutes,
    weatherBufferMinutes: response.breakdown.weather_buffer_minutes,
    totalBudgetMinutes: response.total_time_budget_minutes,
    distanceText,
    congestionLevel,
    provider: response.breakdown.data_source,
    confidenceScore: response.breakdown.confidence_score,
    isLoading: false,
    error: null,
    lastUpdated: new Date(response.calculation_timestamp),
  };
}

// ---------------------------------------------------------------------------
// Convert backend ETAPreviewResponse → ETALivePreview
// ---------------------------------------------------------------------------

export function previewFromPreviewResponse(
  response: ETAPreviewResponse,
  distanceText: string,
  congestionLevel: string
): ETALivePreview {
  return {
    wakeTime: response.recommended_wake_time,
    leaveTime: response.recommended_leave_time,
    arrivalTime: response.expected_arrival_time,
    plannedArrivalTime: response.planned_arrival_time,
    travelMinutes: response.total_travel_minutes,
    baseMinutes: response.total_travel_minutes - response.traffic_delay_minutes,
    trafficDelayMinutes: response.traffic_delay_minutes,
    safetyBufferMinutes: response.safety_buffer_minutes,
    weatherBufferMinutes: 0,
    totalBudgetMinutes: response.total_budget_minutes,
    distanceText,
    congestionLevel,
    provider: response.data_source,
    confidenceScore: response.confidence_score,
    isLoading: false,
    error: null,
    lastUpdated: new Date(),
  };
}
