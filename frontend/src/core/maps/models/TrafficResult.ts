import { MapProviderName } from "./types";

export type CongestionLevel = "clear" | "moderate" | "heavy" | "severe";

export interface TrafficIncident {
  id: string;
  type: "accident" | "construction" | "congestion" | "road_closure" | "weather_hazard";
  description: string;
  severity: "low" | "medium" | "critical";
  delaySeconds: number;
}

/**
 * Normalized Traffic Result.
 * Standard contract across Google Traffic and Mapbox Traffic v1.
 */
export interface TrafficResult {
  congestionLevel: CongestionLevel;
  delaySeconds: number;
  averageSpeedKmh: number;
  provider: MapProviderName;
  timestamp: string;
  incidents: TrafficIncident[];
  commuteImpact: "negligible" | "minor" | "moderate" | "critical";
}
