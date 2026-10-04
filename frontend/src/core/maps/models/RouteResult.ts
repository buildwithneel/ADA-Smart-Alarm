import { GeoPoint, MapProviderName } from "./types";

export interface RouteStep {
  instruction: string;
  distanceMeters: number;
  durationSeconds: number;
  startLocation: GeoPoint;
  endLocation: GeoPoint;
}

/**
 * Normalized Route Result.
 * Standard contract across Google Maps Routes API and Mapbox Directions API.
 * Future ETA Engine consumes this directly without knowing underlying provider.
 */
export interface RouteResult {
  /** Total route distance in meters */
  distanceMeters: number;
  /** Normal baseline duration in seconds without heavy traffic */
  durationSeconds: number;
  /** Duration in seconds factoring in live traffic conditions */
  trafficDurationSeconds: number;
  /** Encoded polyline or GeoJSON LineString geometry string */
  routeGeometry: string;
  /** Starting location GPS coordinates */
  startLocation: GeoPoint;
  /** Destination GPS coordinates */
  destination: GeoPoint;
  /** Which provider generated this result */
  provider: MapProviderName;
  /** Timestamp when the route was calculated */
  timestamp: string;
  /** Formatted human-readable summaries */
  summary: {
    formattedDistance: string; // e.g. "34.2 km"
    formattedDuration: string; // e.g. "38 min"
    formattedTrafficDelay: string; // e.g. "+8 min"
    congestionLevel: "low" | "moderate" | "heavy" | "severe";
  };
  /** Optional granular turn-by-turn steps */
  steps?: RouteStep[];
}
