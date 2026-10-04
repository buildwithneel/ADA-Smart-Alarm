import { ITrafficProvider } from "../../interfaces/ITrafficProvider";
import { GeoPoint } from "../../models/types";
import { TrafficResult } from "../../models/TrafficResult";

/**
 * Mapbox Traffic v1 data provider implementation.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In real implementation: queries Mapbox Matrix API with `annotations=duration,distance`
 * and Mapbox Traffic vector tiles / incidents API.
 */
export class MapboxTrafficProvider implements ITrafficProvider {
  readonly name = "mapbox" as const;

  constructor(public readonly accessToken?: string) {}

  async getTrafficConditions(_origin: GeoPoint, _destination: GeoPoint): Promise<TrafficResult> {
    return {
      congestionLevel: "moderate",
      delaySeconds: 420, // +7 mins
      averageSpeedKmh: 43,
      provider: "mapbox",
      timestamp: new Date().toISOString(),
      commuteImpact: "minor",
      incidents: [
        {
          id: "inc-mb-1",
          type: "congestion",
          description: "Moderate slowdown on Changa link road",
          severity: "low",
          delaySeconds: 240,
        },
      ],
    };
  }
}
