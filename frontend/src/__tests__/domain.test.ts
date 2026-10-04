import { describe, it, expect } from "vitest";
import { formatMinutes, formatTo12Hour } from "@/core/utils/time";
import { calculateHaversineDistance } from "@/core/utils/geo";
import { mapDomainService } from "@/core/maps";
import { useToastStore, toast } from "@/core/toast/useToast";

describe("ADA Core Utility Calculations", () => {
  it("formats minute durations correctly into hours and minutes", () => {
    expect(formatMinutes(38)).toBe("38m");
    expect(formatMinutes(75)).toBe("1h 15m");
    expect(formatMinutes(120)).toBe("2h");
  });

  it("converts 24-hour time strings to 12-hour AM/PM format accurately", () => {
    expect(formatTo12Hour("09:00")).toBe("9:00 AM");
    expect(formatTo12Hour("19:45")).toBe("7:45 PM");
    expect(formatTo12Hour("00:15")).toBe("12:15 AM");
  });

  it("calculates great-circle Haversine distance between coordinates", () => {
    // Distance between Gandhinagar and CHARUSAT (~50-60 km)
    const distance = calculateHaversineDistance(
      { latitude: 23.2156, longitude: 72.6369 },
      { latitude: 22.5996, longitude: 72.8205 }
    );
    expect(distance).toBeGreaterThan(50);
    expect(distance).toBeLessThan(90);
  });
});

describe("Dual Map Provider & Domain Service", () => {
  it("computes normalized RouteResult without vendor leaking", async () => {
    const route = await mapDomainService.calculateCommuteRoute({
      origin: { latitude: 23.2156, longitude: 72.6369 },
      destination: { latitude: 22.5996, longitude: 72.8205 },
      transportMode: "driving",
    });

    expect(route).toBeDefined();
    expect(route.distanceMeters).toBeGreaterThan(0);
    expect(route.durationSeconds).toBeGreaterThan(0);
    expect(route.trafficDurationSeconds).toBeGreaterThanOrEqual(route.durationSeconds);
    expect(["google", "mapbox"]).toContain(route.provider);
    expect(route.summary.formattedDuration).toBeDefined();
  });

  it("returns normalized geocoding coordinates for destination queries", async () => {
    const results = await mapDomainService.searchAddress("CHARUSAT University");
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].latitude).toBeCloseTo(22.5996, 2);
    expect(results[0].longitude).toBeCloseTo(72.8205, 2);
    expect(["google", "mapbox"]).toContain(results[0].provider);
  });

  it("extracts corridor traffic conditions with normalized congestion levels", async () => {
    const traffic = await mapDomainService.getCorridorTraffic(
      { latitude: 23.2156, longitude: 72.6369 },
      { latitude: 22.5996, longitude: 72.8205 }
    );
    expect(traffic).toBeDefined();
    expect(["clear", "moderate", "heavy", "severe"]).toContain(traffic.congestionLevel);
    expect(traffic.delaySeconds).toBeGreaterThanOrEqual(0);
  });
});

describe("Toast Notification Store", () => {
  it("enqueues and clears toast notifications cleanly", () => {
    toast.success("Test Alarm Created", "Wake time dynamically computed.");
    const toasts = useToastStore.getState().toasts;
    expect(toasts.length).toBeGreaterThan(0);
    expect(toasts[toasts.length - 1].title).toBe("Test Alarm Created");

    useToastStore.getState().removeToast(toasts[toasts.length - 1].id);
    const updated = useToastStore.getState().toasts;
    expect(updated.find((t) => t.title === "Test Alarm Created")).toBeUndefined();
  });
});
