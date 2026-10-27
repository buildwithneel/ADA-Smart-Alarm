import { describe, expect, it } from "vitest";
import { LocationManager } from "../src/tracking/LocationManager.js";
import {
  JourneyAlertEvent,
  JourneyLocationFix,
  JourneyState,
  RouteRequestDto,
  RouteResultDto,
} from "@ada/shared";

describe("LocationManager Tracking Suite", () => {
  const baseTime = 1714546800000;
  const destLat = 22.5996;
  const destLng = 72.8205;

  const mockRouteProvider = async (req: RouteRequestDto): Promise<RouteResultDto> => {
    return {
      origin: { latitude: req.origin.latitude, longitude: req.origin.longitude },
      destination: { latitude: req.destination.latitude, longitude: req.destination.longitude },
      distance_meters: 5000,
      duration_seconds: 600,
      traffic_duration_seconds: 720,
      route_geometry: "",
      provider: "Mock Maps",
      is_traffic_aware: true,
    };
  };

  it("processes valid fix and sets initial ACTIVE_TRACKING state", async () => {
    const manager = new LocationManager(mockRouteProvider, () => baseTime);
    manager.startTracking({
      journeyId: "journey-1",
      destinationLat: destLat,
      destinationLng: destLng,
    });

    const fix: JourneyLocationFix = {
      latitude: 22.58,
      longitude: 72.80,
      accuracyMeters: 10,
      timestampEpochMs: baseTime,
    };

    const update = await manager.processLocationFix(fix);

    expect(update.state).toBe(JourneyState.ACTIVE_TRACKING);
    expect(update.etaResult).not.toBeNull();
    expect(update.etaResult?.isTrafficAware).toBe(true);
    expect(update.etaResult?.remainingDurationSeconds).toBe(720);
  });

  it("flags inaccurate GPS fix as TRACKING_DEGRADED", async () => {
    const manager = new LocationManager(mockRouteProvider, () => baseTime);
    manager.startTracking({
      journeyId: "journey-1",
      destinationLat: destLat,
      destinationLng: destLng,
    });

    const badFix: JourneyLocationFix = {
      latitude: 22.58,
      longitude: 72.80,
      accuracyMeters: 80, // > 50m
      timestampEpochMs: baseTime,
    };

    const update = await manager.processLocationFix(badFix);

    expect(update.state).toBe(JourneyState.TRACKING_DEGRADED);
    expect(update.alertEvent).toBe(JourneyAlertEvent.TRACKING_DEGRADED);
  });

  it("detects approaching threshold (<= 1000m) and triggers alert exactly once", async () => {
    const nearRouteProvider = async (): Promise<RouteResultDto> => ({
      origin: {},
      destination: {},
      distance_meters: 800,
      duration_seconds: 120,
      traffic_duration_seconds: 120,
      route_geometry: "",
      provider: "Mock",
      is_traffic_aware: false,
    });

    let currentTime = baseTime;
    const manager = new LocationManager(nearRouteProvider, () => currentTime);
    manager.startTracking({
      journeyId: "journey-1",
      destinationLat: destLat,
      destinationLng: destLng,
    });

    const fix: JourneyLocationFix = {
      latitude: destLat - 0.005,
      longitude: destLng,
      accuracyMeters: 15,
      timestampEpochMs: baseTime,
    };

    // First time under 1000m -> fires approaching alert
    const update1 = await manager.processLocationFix(fix);
    expect(update1.state).toBe(JourneyState.APPROACHING);
    expect(update1.alertEvent).toBe(JourneyAlertEvent.APPROACHING_ALERT);

    // Second fix still under 1000m -> maintains approaching state, alertEvent is undefined (no duplicate)
    currentTime = baseTime + 10000;
    const update2 = await manager.processLocationFix({
      ...fix,
      timestampEpochMs: currentTime,
    });
    expect(update2.state).toBe(JourneyState.APPROACHING);
    expect(update2.alertEvent).toBeUndefined();
  });

  it("requires 2 consecutive accurate hits within arrival threshold (<= 100m) to confirm ARRIVED", async () => {
    const arrivedRouteProvider = async (): Promise<RouteResultDto> => ({
      origin: {},
      destination: {},
      distance_meters: 50,
      duration_seconds: 10,
      traffic_duration_seconds: 10,
      route_geometry: "",
      provider: "Mock",
      is_traffic_aware: false,
    });

    let currentTime = baseTime;
    const manager = new LocationManager(arrivedRouteProvider, () => currentTime);
    manager.startTracking({
      journeyId: "journey-1",
      destinationLat: destLat,
      destinationLng: destLng,
      arrivalThresholdMeters: 100,
    });

    const atDestinationFix1: JourneyLocationFix = {
      latitude: destLat,
      longitude: destLng,
      accuracyMeters: 10,
      timestampEpochMs: baseTime,
    };

    // Hit 1: 50m distance, but consecutive count = 1 -> not yet arrived
    const update1 = await manager.processLocationFix(atDestinationFix1);
    expect(update1.state).not.toBe(JourneyState.ARRIVED);

    // Hit 2: 50m distance, consecutive count = 2 -> Confirmed arrival
    currentTime = baseTime + 5000;
    const update2 = await manager.processLocationFix({
      ...atDestinationFix1,
      timestampEpochMs: currentTime,
    });
    expect(update2.state).toBe(JourneyState.ARRIVED);
    expect(update2.alertEvent).toBe(JourneyAlertEvent.ARRIVAL_CONFIRMED);
    expect(manager.isActive()).toBe(false); // Tracking terminated automatically
  });
});
