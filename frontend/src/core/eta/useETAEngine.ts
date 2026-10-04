/**
 * useETAEngine — React hook for ADA's ETA Calculation Engine.
 *
 * Responsibilities:
 * 1. Optimistic instant preview using client-side pure ETA math
 * 2. Debounced background API call to /eta/preview for accurate backend result
 * 3. Automatic recalculation on parameter change (arrival time, transport mode, etc.)
 * 4. Route data integration (if RouteResult is available, pass durations to skip routing)
 * 5. Full state management: loading, error, confidence display
 *
 * Usage:
 *   const { preview, recalculate } = useETAEngine({
 *     origin, destination, desiredArrival, preparationMinutes, safetyBuffer, mode, routeResult
 *   });
 */

import { useCallback, useEffect, useRef, useState } from "react";
import apiClient from "@/core/api/apiClient";
import {
  computeETA,
  computeHeuristicDurations,
  buildLivePreview,
  previewFromPreviewResponse,
} from "@/core/eta/ETACalculationService";
import type { GeoPoint, RouteResult } from "@/core/maps";
import type { ETALivePreview, ETAPreviewRequest, ETAPreviewResponse } from "@/core/types/eta";
import { DEFAULT_ETA_PREVIEW } from "@/core/types/eta";

// Debounce delay in ms for API calls (prevents flooding on slider drag)
const API_DEBOUNCE_MS = 600;

export interface UseETAEngineOptions {
  origin: GeoPoint;
  destination: GeoPoint;
  desiredArrivalTime: string; // "HH:MM" 24h
  preparationMinutes: number;
  safetyBufferMinutes: number;
  transportMode: "driving" | "transit" | "bicycling" | "walking";
  routeResult?: RouteResult | null; // Pass existing RouteResult to skip redundant API call
  enabled?: boolean; // Set to false to pause recalculations
}

export interface UseETAEngineReturn {
  preview: ETALivePreview;
  recalculate: () => void;
}

export function useETAEngine(options: UseETAEngineOptions): UseETAEngineReturn {
  const {
    origin,
    destination,
    desiredArrivalTime,
    preparationMinutes,
    safetyBufferMinutes,
    transportMode,
    routeResult,
    enabled = true,
  } = options;

  const [preview, setPreview] = useState<ETALivePreview>(DEFAULT_ETA_PREVIEW);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ------------------------------------------------------------------
  // Step 1: Instant optimistic preview using client-side math
  // ------------------------------------------------------------------

  const computeOptimisticPreview = useCallback((): ETALivePreview => {
    let baseSecs: number;
    let trafficSecs: number;
    let distanceText = "—";
    let congestion = "unknown";
    let dataSource = "heuristic";
    let confidence = 0.7;

    if (routeResult) {
      // Use existing route data — most accurate, no extra API call
      baseSecs = routeResult.durationSeconds;
      trafficSecs = routeResult.trafficDurationSeconds;
      distanceText = routeResult.summary?.formattedDistance ?? "—";
      congestion = routeResult.summary?.congestionLevel ?? "unknown";
      dataSource = routeResult.provider;
      confidence = routeResult.provider === "google" ? 0.97 : 0.93;
    } else {
      // Haversine heuristic
      const h = computeHeuristicDurations(
        origin.latitude,
        origin.longitude,
        destination.latitude,
        destination.longitude,
        transportMode
      );
      baseSecs = h.baseSecs;
      trafficSecs = h.trafficSecs;
      distanceText = `~${h.distanceKm.toFixed(1)} km`;
      congestion = "unknown";
    }

    const result = computeETA({
      desiredArrivalTime,
      baseDurationSeconds: baseSecs,
      trafficDurationSeconds: trafficSecs,
      preparationMinutes,
      safetyBufferMinutes,
      dataSource,
      confidenceScore: confidence,
    });

    return buildLivePreview(result, distanceText, congestion, false, null);
  }, [
    origin,
    destination,
    desiredArrivalTime,
    preparationMinutes,
    safetyBufferMinutes,
    transportMode,
    routeResult,
  ]);

  // ------------------------------------------------------------------
  // Step 2: Accurate backend API preview (debounced)
  // ------------------------------------------------------------------

  const fetchApiPreview = useCallback(async () => {
    // Cancel previous in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
    }
    abortRef.current = new AbortController();

    // Show loading state
    setPreview((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const payload: ETAPreviewRequest = {
        origin_lat: origin.latitude,
        origin_lng: origin.longitude,
        dest_lat: destination.latitude,
        dest_lng: destination.longitude,
        desired_arrival_time: desiredArrivalTime,
        preparation_time_minutes: preparationMinutes,
        safety_buffer_minutes: safetyBufferMinutes,
        transport_mode: transportMode,
        // If we already have route data, pass durations to skip backend routing
        ...(routeResult
          ? {
              base_duration_seconds: routeResult.durationSeconds,
              traffic_duration_seconds: routeResult.trafficDurationSeconds,
            }
          : {}),
      };

      const response = await apiClient.post<ETAPreviewResponse>("/eta/preview", payload, {
        signal: abortRef.current.signal,
      });

      const distanceText =
        routeResult?.summary?.formattedDistance ?? "—";
      const congestion =
        routeResult?.summary?.congestionLevel ?? "unknown";

      setPreview(previewFromPreviewResponse(response.data, distanceText, congestion));
    } catch (err: any) {
      if (err?.name === "CanceledError" || err?.code === "ERR_CANCELED") {
        // Aborted — ignore
        return;
      }
      // API call failed → fall back to optimistic preview already displayed
      const optimistic = computeOptimisticPreview();
      setPreview({
        ...optimistic,
        isLoading: false,
        error: "Using estimated travel time (network unavailable)",
      });
    }
  }, [
    origin,
    destination,
    desiredArrivalTime,
    preparationMinutes,
    safetyBufferMinutes,
    transportMode,
    routeResult,
    computeOptimisticPreview,
  ]);

  // ------------------------------------------------------------------
  // Recalculate: show optimistic immediately, queue accurate API call
  // ------------------------------------------------------------------

  const recalculate = useCallback(() => {
    if (!enabled) return;

    // Instantly update with heuristic/route-based optimistic preview
    const optimistic = computeOptimisticPreview();
    setPreview({ ...optimistic, isLoading: true });

    // Debounce the actual API call
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchApiPreview();
    }, API_DEBOUNCE_MS);
  }, [enabled, computeOptimisticPreview, fetchApiPreview]);

  // ------------------------------------------------------------------
  // Auto-recalculate on any dependency change
  // ------------------------------------------------------------------

  useEffect(() => {
    recalculate();

    return () => {
      // Cleanup on unmount
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (abortRef.current) abortRef.current.abort();
    };
  }, [recalculate]);

  return { preview, recalculate };
}
