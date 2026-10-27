import { describe, expect, it } from "vitest";
import {
  DEFAULT_APPROACHING_THRESHOLD_METERS,
  DEFAULT_ARRIVAL_THRESHOLD_METERS,
  DEFAULT_TRACKING_LEAD_MINUTES,
  DynamicEtaEngine,
} from "../src/engine/DynamicEtaEngine.js";
import {
  EtaSource,
  JourneyAlertEvent,
  JourneyLocationFix,
  JourneyState,
  RouteResultDto,
} from "../src/contracts/models.js";
import { decodePolyline } from "../src/geo/polyline.js";
import { haversineMeters } from "../src/geo/haversine.js";
import { JourneyStateMachine } from "../src/state/JourneyStateMachine.js";

describe("DynamicEtaEngine Mathematical Suite", () => {
  const baseTime = 1714546800000; // 07:00:00 UTC
  const charusatLat = 22.5996;
  const charusatLng = 72.8205;
  const ahmedabadLat = 23.0225;
  const ahmedabadLng = 72.5714;

  it("calculates tracking start time with default 15m lead time", () => {
    const departure = baseTime + 60 * 60 * 1000; // 08:00
    const start = DynamicEtaEngine.calculateTrackingStartTime(departure, DEFAULT_TRACKING_LEAD_MINUTES);
    expect(start).toBe(departure - 15 * 60 * 1000);
  });

  it("rejects negative lead time", () => {
    expect(() => DynamicEtaEngine.calculateTrackingStartTime(baseTime, -5)).toThrow();
  });

  it("validates location fixes: accepts accurate fresh fix", () => {
    const fix: JourneyLocationFix = {
      latitude: ahmedabadLat,
      longitude: ahmedabadLng,
      accuracyMeters: 10,
      timestampEpochMs: baseTime,
    };
    expect(DynamicEtaEngine.isLocationFixValid(fix, 50, 60000, baseTime + 10000)).toBe(true);
  });

  it("rejects inaccurate fixes (> 50m) and stale fixes (> 60s)", () => {
    const inaccurateFix: JourneyLocationFix = {
      latitude: ahmedabadLat,
      longitude: ahmedabadLng,
      accuracyMeters: 75,
      timestampEpochMs: baseTime,
    };
    expect(DynamicEtaEngine.isLocationFixValid(inaccurateFix, 50, 60000, baseTime + 5000)).toBe(false);

    const staleFix: JourneyLocationFix = {
      latitude: ahmedabadLat,
      longitude: ahmedabadLng,
      accuracyMeters: 10,
      timestampEpochMs: baseTime - 70000,
    };
    expect(DynamicEtaEngine.isLocationFixValid(staleFix, 50, 60000, baseTime)).toBe(false);
  });

  it("rejects fixes from more than 5 seconds in future", () => {
    const futureFix: JourneyLocationFix = {
      latitude: ahmedabadLat,
      longitude: ahmedabadLng,
      accuracyMeters: 10,
      timestampEpochMs: baseTime + 10000,
    };
    expect(DynamicEtaEngine.isLocationFixValid(futureFix, 50, 60000, baseTime)).toBe(false);
  });

  it("detects unrealistic GPS velocity jumps (> 45 m/s with moderate accuracy)", () => {
    const fix1: JourneyLocationFix = {
      latitude: 23.00,
      longitude: 72.50,
      accuracyMeters: 20,
      timestampEpochMs: baseTime,
    };
    // 5km away after 10 seconds => 500 m/s
    const fix2: JourneyLocationFix = {
      latitude: 23.045,
      longitude: 72.50,
      accuracyMeters: 25,
      timestampEpochMs: baseTime + 10000,
    };

    expect(DynamicEtaEngine.isGpsJump(fix1, fix2, 45)).toBe(true);
  });

  it("allows realistic highway travel (~30 m/s = ~108 km/h)", () => {
    const fix1: JourneyLocationFix = {
      latitude: 23.000,
      longitude: 72.500,
      accuracyMeters: 8,
      timestampEpochMs: baseTime,
    };
    // 300 meters in 10 seconds => 30 m/s
    const fix2: JourneyLocationFix = {
      latitude: 23.0027,
      longitude: 72.500,
      accuracyMeters: 8,
      timestampEpochMs: baseTime + 10000,
    };

    expect(DynamicEtaEngine.isGpsJump(fix1, fix2, 45)).toBe(false);
  });

  it("derives dynamic ETA from provider without double-counting elapsed travel time", () => {
    const fix: JourneyLocationFix = {
      latitude: ahmedabadLat,
      longitude: ahmedabadLng,
      accuracyMeters: 12,
      timestampEpochMs: baseTime,
    };
    const routeResult: RouteResultDto = {
      origin: { latitude: ahmedabadLat, longitude: ahmedabadLng },
      destination: { latitude: charusatLat, longitude: charusatLng },
      distance_meters: 65000,
      duration_seconds: 4200,
      traffic_duration_seconds: 4800, // 80 min with traffic
      route_geometry: "",
      provider: "Google Maps",
      is_traffic_aware: true,
    };

    const eta = DynamicEtaEngine.calculateEtaFromProvider(fix, routeResult, baseTime);

    expect(eta.isTrafficAware).toBe(true);
    expect(eta.source).toBe(EtaSource.TRAFFIC_AWARE_PROVIDER);
    expect(eta.remainingDurationSeconds).toBe(4800);
    // Predicted arrival = fix.timestampEpochMs + remainingDurationSeconds * 1000
    expect(eta.predictedArrivalEpochMs).toBe(baseTime + 4800 * 1000);
  });

  it("computes fallback Great-Circle ETA with explicit non-traffic indicator", () => {
    const fix: JourneyLocationFix = {
      latitude: ahmedabadLat,
      longitude: ahmedabadLng,
      accuracyMeters: 10,
      timestampEpochMs: baseTime,
    };

    const fallback = DynamicEtaEngine.calculateFallbackEta(fix, charusatLat, charusatLng, 11.11, baseTime);

    expect(fallback.isTrafficAware).toBe(false);
    expect(fallback.source).toBe(EtaSource.NON_TRAFFIC_FALLBACK);
    expect(fallback.providerName).toBe("Fallback Heuristic");
    expect(fallback.remainingDistanceMeters).toBeGreaterThan(45000);
    expect(fallback.remainingDurationSeconds).toBeGreaterThan(3000);
    expect(fallback.predictedArrivalEpochMs).toBe(baseTime + fallback.remainingDurationSeconds * 1000);
  });

  it("enforces route recalculation cooldown (30s) and progress thresholds", () => {
    const fix1: JourneyLocationFix = {
      latitude: 23.00,
      longitude: 72.50,
      accuracyMeters: 10,
      timestampEpochMs: baseTime,
    };

    // 10s later -> rejected by cooldown
    expect(
      DynamicEtaEngine.shouldRecalculateRoute(false, baseTime, null, fix1, baseTime + 10000)
    ).toBe(false);

    // 40s later, deviated -> immediate recalculation allowed
    expect(
      DynamicEtaEngine.shouldRecalculateRoute(true, baseTime, null, fix1, baseTime + 40000)
    ).toBe(true);

    // Stale result (> 300s) -> recalculation allowed
    expect(
      DynamicEtaEngine.shouldRecalculateRoute(false, baseTime, null, fix1, baseTime + 301000)
    ).toBe(true);
  });

  it("evaluates route deviation against decoded corridor polyline", () => {
    const encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@";
    const points = decodePolyline(encoded);
    expect(points.length).toBeGreaterThan(0);

    const onRouteFix: JourneyLocationFix = {
      latitude: points[0][0],
      longitude: points[0][1],
      accuracyMeters: 5,
      timestampEpochMs: baseTime,
    };
    expect(DynamicEtaEngine.isRouteDeviation(onRouteFix, points, 250)).toBe(false);

    // 1 km away from route point
    const deviatedFix: JourneyLocationFix = {
      latitude: points[0][0] + 0.01,
      longitude: points[0][1] + 0.01,
      accuracyMeters: 5,
      timestampEpochMs: baseTime,
    };
    expect(DynamicEtaEngine.isRouteDeviation(deviatedFix, points, 250)).toBe(true);
  });

  it("triggers approaching alert idempotently (<= 1,000m)", () => {
    expect(DynamicEtaEngine.checkApproachingAlert(1200, 1000, false)).toBe(false);
    expect(DynamicEtaEngine.checkApproachingAlert(950, 1000, false)).toBe(true);
    // If already alerted, returns false
    expect(DynamicEtaEngine.checkApproachingAlert(950, 1000, true)).toBe(false);
  });

  it("confirms arrival with multi-fix requirement (<= 100m, <= 50m accuracy, 2 hits)", () => {
    // 80m distance, 10m accuracy, but only 1 confirmation hit
    expect(DynamicEtaEngine.checkArrivalConfirmation(80, 10, 100, 1, 2)).toBe(false);

    // 80m distance, 10m accuracy, 2 confirmation hits -> Confirmed
    expect(DynamicEtaEngine.checkArrivalConfirmation(80, 10, 100, 2, 2)).toBe(true);

    // Inaccurate fix (60m accuracy) -> Rejected even if distance <= 100m
    expect(DynamicEtaEngine.checkArrivalConfirmation(50, 60, 100, 2, 2)).toBe(false);
  });

  it("executes valid JourneyStateMachine transitions and guards terminal states", () => {
    const res1 = JourneyStateMachine.transition(JourneyState.SCHEDULED, { type: "START_TRACKING" });
    expect(res1.nextState).toBe(JourneyState.ACTIVE_TRACKING);
    expect(res1.alertEvent).toBe(JourneyAlertEvent.TRACKING_STARTED);

    const res2 = JourneyStateMachine.transition(JourneyState.ACTIVE_TRACKING, { type: "APPROACHING" });
    expect(res2.nextState).toBe(JourneyState.APPROACHING);
    expect(res2.alertEvent).toBe(JourneyAlertEvent.APPROACHING_ALERT);

    const res3 = JourneyStateMachine.transition(JourneyState.APPROACHING, { type: "ARRIVED" });
    expect(res3.nextState).toBe(JourneyState.ARRIVED);
    expect(res3.alertEvent).toBe(JourneyAlertEvent.ARRIVAL_CONFIRMED);

    // Terminal state guard: cannot start tracking once arrived
    const res4 = JourneyStateMachine.transition(JourneyState.ARRIVED, { type: "START_TRACKING" });
    expect(res4.isValid).toBe(false);
    expect(res4.nextState).toBe(JourneyState.ARRIVED);
  });
});
