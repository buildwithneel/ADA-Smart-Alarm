// @vitest-environment jsdom
import { describe, it, expect, beforeEach, vi } from "vitest";
import { locationService } from "@/core/location/LocationService";
import { MapController } from "@/core/maps/services/MapController";
import { locationApiClient } from "@/core/api/locationClient";

// In-memory mock storage if environment doesn't provide full Web Storage
class MockLocalStorage {
  private store: Record<string, string> = {};
  getItem(key: string) {
    return this.store[key] || null;
  }
  setItem(key: string, val: string) {
    this.store[key] = val;
  }
  removeItem(key: string) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

if (typeof window !== "undefined") {
  if (!window.localStorage) {
    // @ts-ignore
    window.localStorage = new MockLocalStorage();
  }
}

describe("Frontend LocationService Tests", () => {
  beforeEach(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.clear();
    }
    vi.restoreAllMocks();
  });

  it("validates coordinate boundaries accurately", () => {
    expect(locationService.isValidCoordinates(22.5996, 72.8205)).toBe(true);
    expect(locationService.isValidCoordinates(0, 0)).toBe(true);
    expect(locationService.isValidCoordinates(90, 180)).toBe(true);
    expect(locationService.isValidCoordinates(-90, -180)).toBe(true);

    // Invalid coordinates
    expect(locationService.isValidCoordinates(91.5, 72.0)).toBe(false);
    expect(locationService.isValidCoordinates(-95.0, 72.0)).toBe(false);
    expect(locationService.isValidCoordinates(22.0, 185.0)).toBe(false);
    expect(locationService.isValidCoordinates(22.0, -181.0)).toBe(false);
    expect(locationService.isValidCoordinates(NaN, 72.0)).toBe(false);
  });

  it("normalizes GeolocationPosition with strict domain types and null telemetry", () => {
    const mockPos = {
      coords: {
        latitude: 22.5996,
        longitude: 72.8205,
        accuracy: 12.5,
        altitude: null,
        altitudeAccuracy: null,
        heading: null,
        speed: null,
      },
      timestamp: 1710000000000,
    } as unknown as GeolocationPosition;


    const normalized = locationService.normalizePosition(mockPos);
    expect(normalized.latitude).toBe(22.5996);
    expect(normalized.longitude).toBe(72.8205);
    expect(normalized.accuracyMeters).toBe(12.5);
    expect(normalized.altitude).toBeNull();
    expect(normalized.heading).toBeNull();
    expect(normalized.speed).toBeNull();
    expect(normalized.timestamp).toBe(1710000000000);
  });

  it("tracks permanent permission denial to prevent user harassment", async () => {
    window.localStorage.setItem("ada_location_permanently_denied", "true");
    const status = await locationService.getPermissionStatus();
    expect(status).toBe("denied_permanently");

    // Resetting allows user to re-attempt
    locationService.resetPermissionStatus();
    expect(window.localStorage.getItem("ada_location_permanently_denied")).toBeNull();
  });

  it("acquires instantaneous geolocation when navigator succeeds", async () => {
    const mockGeolocation = {
      getCurrentPosition: vi.fn((success) =>
        success({
          coords: {
            latitude: 23.0225,
            longitude: 72.5714,
            accuracy: 8,
            altitude: null,
            altitudeAccuracy: null,
            heading: null,
            speed: null,
          },
          timestamp: Date.now(),
        })
      ),
      watchPosition: vi.fn(() => 42),
      clearWatch: vi.fn(),
    };

    // @ts-ignore
    global.navigator.geolocation = mockGeolocation;

    const loc = await locationService.getCurrentPosition();
    expect(loc.latitude).toBe(23.0225);
    expect(loc.longitude).toBe(72.5714);
    expect(mockGeolocation.getCurrentPosition).toHaveBeenCalled();
  });

  it("handles position watch and unwatch lifecycle cleanly", () => {
    const clearWatchMock = vi.fn();
    // @ts-ignore
    global.navigator.geolocation = {
      watchPosition: vi.fn(() => 101),
      clearWatch: clearWatchMock,
      getCurrentPosition: vi.fn(),
    };

    const watchId = locationService.watchPosition(() => {});
    expect(watchId).toBe(101);

    locationService.stopWatching(watchId);
    expect(clearWatchMock).toHaveBeenCalledWith(101);
  });
});

describe("Frontend MapController Tests", () => {
  it("controls zoom boundaries and pans correctly", () => {
    let lastState: any = null;
    const controller = new MapController({ latitude: 22.5, longitude: 72.8 }, 12, (s) => {
      lastState = s;
    });

    controller.zoomIn();
    expect(lastState.zoom).toBe(13);

    controller.zoomOut();
    expect(lastState.zoom).toBe(12);

    controller.setCenter({ latitude: 23.0, longitude: 72.5 }, 15);
    expect(lastState.center.latitude).toBe(23.0);
    expect(lastState.zoom).toBe(15);
  });

  it("calculates bounding box zoom to fit route corridor", () => {
    let state: any = null;
    const controller = new MapController({ latitude: 0, longitude: 0 }, 10, (s) => {
      state = s;
    });

    // Fit route between Gandhinagar and CHARUSAT (~0.6 lat difference)
    controller.fitRoute(
      { latitude: 23.2156, longitude: 72.6369 },
      { latitude: 22.5996, longitude: 72.8205 }
    );

    expect(state.center.latitude).toBeCloseTo(22.9076, 2);
    expect(state.center.longitude).toBeCloseTo(72.7287, 2);
    expect(state.zoom).toBeGreaterThanOrEqual(10);
    expect(state.zoom).toBeLessThanOrEqual(14);
  });
});

describe("LocationApiClient Fallback and Resilience", () => {
  it("returns fallback geocoding results gracefully when backend offline", async () => {
    const results = await locationApiClient.searchGeocoding("CHARUSAT");
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].latitude).toBeCloseTo(22.5996, 2);
  });

  it("returns fallback route calculation with separated traffic delays", async () => {
    const route = await locationApiClient.calculateRoute({
      origin: { latitude: 23.2156, longitude: 72.6369 },
      destination: { latitude: 22.5996, longitude: 72.8205 },
      transportMode: "driving",
    });

    expect(route).toBeDefined();
    expect(route.durationSeconds).toBeGreaterThan(0);
    expect(route.trafficDurationSeconds).toBeGreaterThanOrEqual(route.durationSeconds);
    expect(route.summary.formattedDuration).toBeDefined();
  });
});
