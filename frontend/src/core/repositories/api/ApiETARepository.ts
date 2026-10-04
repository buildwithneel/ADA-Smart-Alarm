/**
 * ApiETARepository — Real API ETA repository implementation.
 *
 * Calls the ADA backend /api/v1/eta/ endpoints.
 * Falls back to pure frontend ETACalculationService when backend is unreachable.
 */

import apiClient from "@/core/api/apiClient";
import {
  computeETA,
  computeHeuristicDurations,
} from "@/core/eta/ETACalculationService";
import type { IETARepository, ETARequest } from "../interfaces/ETARepository";
import type {
  AlarmCalculationPreview,
  TransportMode,
} from "@/core/types/alarm";
import type {
  ETACalculateResponse,
  ETAPreviewResponse,
  AlarmETAUpdateResult,
  ETAPreviewRequest,
} from "@/core/types/eta";

export class ApiETARepository implements IETARepository {
  /**
   * Calls /eta/preview for a lightweight live preview.
   * Falls back to client-side pure computation if backend unavailable.
   */
  async calculateETA(request: ETARequest): Promise<AlarmCalculationPreview> {
    const payload: ETAPreviewRequest = {
      origin_lat: request.originLat,
      origin_lng: request.originLng,
      dest_lat: request.destinationLat,
      dest_lng: request.destinationLng,
      desired_arrival_time: request.desiredArrival,
      preparation_time_minutes: request.routineMinutes,
      safety_buffer_minutes: request.bufferMinutes,
      transport_mode: this._normalizeMode(request.transportMode),
    };

    try {
      const response = await apiClient.post<ETAPreviewResponse>(
        "/eta/preview",
        payload
      );
      const d = response.data;
      return {
        travel_minutes: d.total_travel_minutes,
        traffic_delay_minutes: d.traffic_delay_minutes,
        recommended_leave_time: d.recommended_leave_time,
        recommended_wake_time: d.recommended_wake_time,
        weather_summary: `Route via ${d.data_source.toUpperCase()}`,
        confidence_score: d.confidence_score,
      };
    } catch (err) {
      console.warn(
        "ApiETARepository: /eta/preview failed, using client-side heuristic:",
        err
      );
      return this._clientFallback(request);
    }
  }

  /**
   * Calls /eta/alarms/{alarm_id}/evaluate to re-evaluate and persist alarm ETA.
   */
  async evaluateAlarm(alarmId: string): Promise<AlarmETAUpdateResult> {
    const response = await apiClient.post<AlarmETAUpdateResult>(
      `/eta/alarms/${alarmId}/evaluate`,
      {}
    );
    return response.data;
  }

  /**
   * Calls /eta/calculate for a full ETA calculation with breakdown.
   * Requires route durations to skip redundant backend routing call.
   */
  async calculateWithBreakdown(
    params: ETAPreviewRequest & {
      override_base_duration_seconds?: number;
      override_traffic_duration_seconds?: number;
    }
  ): Promise<ETACalculateResponse> {
    const response = await apiClient.post<ETACalculateResponse>(
      "/eta/calculate",
      params
    );
    return response.data;
  }

  // ------------------------------------------------------------------
  // Private: client-side Haversine heuristic fallback
  // ------------------------------------------------------------------

  private _clientFallback(request: ETARequest): AlarmCalculationPreview {
    const { baseSecs, trafficSecs } = computeHeuristicDurations(
      request.originLat,
      request.originLng,
      request.destinationLat,
      request.destinationLng,
      request.transportMode
    );

    const result = computeETA({
      desiredArrivalTime: request.desiredArrival,
      baseDurationSeconds: baseSecs,
      trafficDurationSeconds: trafficSecs,
      preparationMinutes: request.routineMinutes,
      safetyBufferMinutes: request.bufferMinutes,
      dataSource: "heuristic",
      confidenceScore: 0.7,
    });

    const format12h = (d: Date) => {
      const h = d.getHours();
      const m = d.getMinutes();
      const period = h < 12 ? "AM" : "PM";
      const h12 = h % 12 || 12;
      return `${String(h12).padStart(2, "0")}:${String(m).padStart(2, "0")} ${period}`;
    };

    return {
      travel_minutes: result.totalTravelMinutes,
      traffic_delay_minutes: result.trafficDelayMinutes,
      recommended_leave_time: format12h(result.leaveTime),
      recommended_wake_time: format12h(result.wakeTime),
      weather_summary: "Heuristic estimate (no network)",
      confidence_score: result.confidenceScore,
    };
  }

  private _normalizeMode(
    mode: TransportMode
  ): "driving" | "transit" | "bicycling" | "walking" {
    if (mode === "bicycling") return "bicycling";
    return mode as "driving" | "transit" | "walking";
  }
}
