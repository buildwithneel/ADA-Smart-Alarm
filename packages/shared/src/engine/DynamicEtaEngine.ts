/**
 * Pure TypeScript Mathematical Calculation Engine for Dynamic Journey Monitoring & ETA Tracking.
 *
 * Strict 1-to-1 port of Kotlin engine: `com.thinkx.ada.domain.journey.engine.DynamicEtaEngine`.
 *
 * Implements ADA's destination-aware dynamic ETA contract:
 * 1. Tracking start calculation from scheduled departure and lead time.
 * 2. GPS accuracy filtering, staleness rejection, and velocity jump protection.
 * 3. Traffic-aware ETA derivation where elapsed time is never double-counted.
 * 4. Fallback ETA derivation with explicit non-traffic labeling.
 * 5. Route deviation detection against route polyline corridors.
 * 6. Idempotent proximity alert triggers (Approaching: 1,000m, Arrival: 100m).
 */

import {
  DynamicEtaResult,
  EtaSource,
  JourneyLocationFix,
  RouteResultDto,
} from "../contracts/models.js";
import { haversineMeters } from "../geo/haversine.js";

export const DEFAULT_TRACKING_LEAD_MINUTES = 15;
export const DEFAULT_APPROACHING_THRESHOLD_METERS = 1000;
export const DEFAULT_ARRIVAL_THRESHOLD_METERS = 100;

export class DynamicEtaEngine {
  /**
   * Calculates the exact tracking start epoch ms given scheduled departure and lead time.
   */
  static calculateTrackingStartTime(
    scheduledDepartureEpochMs: number,
    trackingLeadMinutes: number = DEFAULT_TRACKING_LEAD_MINUTES
  ): number {
    if (trackingLeadMinutes < 0) {
      throw new Error("Tracking lead time must be non-negative");
    }
    return scheduledDepartureEpochMs - trackingLeadMinutes * 60 * 1000;
  }

  /**
   * Filters out unreliable location fixes based on accuracy, age, and future timestamps.
   */
  static isLocationFixValid(
    fix: JourneyLocationFix,
    maxAccuracyMeters: number = 50,
    maxAgeMs: number = 60000,
    currentTimeMs: number = Date.now()
  ): boolean {
    if (fix.accuracyMeters <= 0 || fix.accuracyMeters > maxAccuracyMeters) {
      return false;
    }
    const age = currentTimeMs - fix.timestampEpochMs;
    if (age > maxAgeMs) {
      return false;
    }
    // Reject timestamp from more than 5 seconds in the future
    if (fix.timestampEpochMs > currentTimeMs + 5000) {
      return false;
    }
    return true;
  }

  /**
   * Detects unrealistic GPS position jumps between consecutive location fixes.
   * Rejects jumps exceeding maxRealisticSpeedMps (default 45 m/s = ~162 km/h) unless accuracy is exceptionally high.
   */
  static isGpsJump(
    previousFix: JourneyLocationFix,
    currentFix: JourneyLocationFix,
    maxRealisticSpeedMps: number = 45
  ): boolean {
    const elapsedSec = (currentFix.timestampEpochMs - previousFix.timestampEpochMs) / 1000.0;
    if (elapsedSec <= 0.5) return false;

    const distanceMeters = haversineMeters(
      previousFix.latitude,
      previousFix.longitude,
      currentFix.latitude,
      currentFix.longitude
    );
    const impliedSpeedMps = distanceMeters / elapsedSec;

    return impliedSpeedMps > maxRealisticSpeedMps && currentFix.accuracyMeters > 15;
  }

  /**
   * Derives a dynamic ETA from a routing provider's result.
   *
   * Invariants:
   * - Provider duration is remaining duration from current position to destination.
   * - predictedArrival = fix.timestampEpochMs + (durationSeconds * 1000).
   * - Elapsed travel time is NOT added twice.
   * - No artificial stop penalty added on top of traffic-aware duration.
   */
  static calculateEtaFromProvider(
    fix: JourneyLocationFix,
    routeResult: RouteResultDto,
    currentTimeEpochMs: number = Date.now()
  ): DynamicEtaResult {
    const durationSeconds =
      routeResult.is_traffic_aware && routeResult.traffic_duration_seconds > 0
        ? routeResult.traffic_duration_seconds
        : routeResult.duration_seconds;

    const predictedArrivalEpochMs = fix.timestampEpochMs + durationSeconds * 1000;

    return {
      predictedArrivalEpochMs,
      remainingDurationSeconds: durationSeconds,
      remainingDistanceMeters: routeResult.distance_meters,
      isTrafficAware: routeResult.is_traffic_aware,
      source: routeResult.is_traffic_aware
        ? EtaSource.TRAFFIC_AWARE_PROVIDER
        : EtaSource.NON_TRAFFIC_FALLBACK,
      providerName: routeResult.provider,
      lastRefreshEpochMs: currentTimeEpochMs,
      isStale: false,
      routeGeometry: routeResult.route_geometry,
    };
  }

  /**
   * Computes a conservative non-traffic fallback ETA using Great-Circle distance
   * and a realistic urban/suburban average velocity (default 40 km/h = ~11.11 m/s).
   * Explicitly marked as non-traffic-aware.
   */
  static calculateFallbackEta(
    fix: JourneyLocationFix,
    destinationLat: number,
    destinationLng: number,
    averageSpeedMps: number = 11.11,
    currentTimeEpochMs: number = Date.now()
  ): DynamicEtaResult {
    const distanceMeters = Math.round(
      haversineMeters(fix.latitude, fix.longitude, destinationLat, destinationLng)
    );
    const durationSeconds =
      distanceMeters > 0 && averageSpeedMps > 0
        ? Math.round(distanceMeters / averageSpeedMps)
        : 0;

    const predictedArrivalEpochMs = fix.timestampEpochMs + durationSeconds * 1000;

    return {
      predictedArrivalEpochMs,
      remainingDurationSeconds: durationSeconds,
      remainingDistanceMeters: distanceMeters,
      isTrafficAware: false,
      source: EtaSource.NON_TRAFFIC_FALLBACK,
      providerName: "Fallback Heuristic",
      lastRefreshEpochMs: currentTimeEpochMs,
      isStale: false,
    };
  }

  /**
   * Determines whether an updated route calculation should be dispatched to the provider.
   * Uses throttling and hysteresis:
   * - Recalculates immediately if confirmed route deviation is detected.
   * - Minimum cooldown of 30s between requests.
   * - Recalculates if user moved >= minDistanceDeltaMeters AND >= minIntervalSec elapsed.
   * - Recalculates if current ETA is stale (> stalenessThresholdMs).
   */
  static shouldRecalculateRoute(
    isDeviated: Boolean,
    lastRequestEpochMs: number,
    lastLocationFix: JourneyLocationFix | null,
    currentFix: JourneyLocationFix,
    currentTimeEpochMs: number = Date.now(),
    minDistanceDeltaMeters: number = 200.0,
    minIntervalSec: number = 180,
    stalenessThresholdMs: number = 300000
  ): boolean {
    const elapsedSinceLastRequestMs = currentTimeEpochMs - lastRequestEpochMs;

    // Never request faster than 30s to respect provider rate limits
    if (elapsedSinceLastRequestMs < 30000) return false;

    // Immediate recalculation upon confirmed route deviation
    if (isDeviated) return true;

    // Recalculate if previous result is stale
    if (elapsedSinceLastRequestMs >= stalenessThresholdMs) return true;

    // Check progress thresholds: distance moved and time elapsed
    const distanceMoved = lastLocationFix
      ? haversineMeters(
          lastLocationFix.latitude,
          lastLocationFix.longitude,
          currentFix.latitude,
          currentFix.longitude
        )
      : Number.MAX_VALUE;
    const timeElapsedSec = elapsedSinceLastRequestMs / 1000;

    return distanceMoved >= minDistanceDeltaMeters && timeElapsedSec >= minIntervalSec;
  }

  /**
   * Evaluates whether current position deviates from route polyline points.
   * If minimum distance exceeds deviationThresholdMeters (default 250m), triggers deviation.
   */
  static isRouteDeviation(
    currentFix: JourneyLocationFix,
    routePoints: Array<[number, number]>,
    deviationThresholdMeters: number = 250.0
  ): boolean {
    if (routePoints.length === 0) return false;

    let minDistance = Number.MAX_VALUE;
    for (const [lat, lng] of routePoints) {
      const dist = haversineMeters(currentFix.latitude, currentFix.longitude, lat, lng);
      if (dist < minDistance) {
        minDistance = dist;
      }
    }

    return minDistance > deviationThresholdMeters;
  }

  /**
   * Checks if approaching destination alert condition is met (<= 1,000m).
   * Idempotent: triggers only once per journey.
   */
  static checkApproachingAlert(
    currentDistanceMeters: number,
    approachingThresholdMeters: number = DEFAULT_APPROACHING_THRESHOLD_METERS,
    alreadyAlerted: boolean = false
  ): boolean {
    if (alreadyAlerted) return false;
    return currentDistanceMeters <= approachingThresholdMeters;
  }

  /**
   * Checks if arrival at destination is confirmed.
   * Requires:
   * 1. Distance <= arrivalThresholdMeters (default 100m).
   * 2. Good GPS accuracy (<= 50m).
   * 3. Multi-fix confirmation count >= requiredConfirmations (prevents single-fix false arrival).
   */
  static checkArrivalConfirmation(
    currentDistanceMeters: number,
    accuracyMeters: number,
    arrivalThresholdMeters: number = DEFAULT_ARRIVAL_THRESHOLD_METERS,
    consecutiveConfirmations: number = 1,
    requiredConfirmations: number = 2
  ): boolean {
    if (accuracyMeters > 50) return false;
    return (
      currentDistanceMeters <= arrivalThresholdMeters &&
      consecutiveConfirmations >= requiredConfirmations
    );
  }
}
