import { ITrafficProvider } from "../../interfaces/ITrafficProvider";
import { GeoPoint } from "../../models/types";
import { TrafficResult } from "../../models/TrafficResult";

/**
 * Google Traffic Data provider implementation.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In real implementation: queries Google Distance Matrix with departure_time=now
 * or Route Matrix API to extract live traffic congestion severity and incidents.
 */
export class GoogleTrafficProvider implements ITrafficProvider {
  readonly name = "google" as const;

  constructor(public readonly apiKey?: string) {}

  async getTrafficConditions(_origin: GeoPoint, _destination: GeoPoint): Promise<TrafficResult> {
    return {
      congestionLevel: "moderate",
      delaySeconds: 480, // +8 mins
      averageSpeedKmh: 42,
      provider: "google",
      timestamp: new Date().toISOString(),
      commuteImpact: "minor",
      incidents: [
        {
          id: "inc-g-1",
          type: "congestion",
          description: "Slow traffic between Anand and Changa Junction",
          severity: "medium",
          delaySeconds: 300,
        },
      ],
    };
  }
}
