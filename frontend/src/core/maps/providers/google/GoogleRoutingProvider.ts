import { IRoutingProvider } from "../../interfaces/IRoutingProvider";
import { RouteRequestOptions } from "../../models/types";
import { RouteResult } from "../../models/RouteResult";

/**
 * Google Maps Routes & Directions API implementation.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In real implementation: calls Google Routes API v2:
 * `POST https://routes.googleapis.com/directions/v2:computeRoutes`
 * with header `X-Goog-Api-Key` and `X-Goog-FieldMask: routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline`
 */
export class GoogleRoutingProvider implements IRoutingProvider {
  readonly name = "google" as const;

  constructor(public readonly apiKey?: string) {}

  async calculateRoute(options: RouteRequestOptions): Promise<RouteResult> {
    // Speed heuristics based on transport mode
    const speedKmh = {
      driving: 45,
      transit: 30,
      bicycling: 15,
      walking: 4.5,
    }[options.transportMode];

    // Compute approximate distance
    const distKm = 34.2;
    const distanceMeters = Math.round(distKm * 1000);
    const durationSeconds = Math.round((distKm / speedKmh) * 3600);
    const trafficDelaySeconds = options.transportMode === "driving" ? 480 : 0; // +8 min traffic
    const trafficDurationSeconds = durationSeconds + trafficDelaySeconds;

    return {
      distanceMeters,
      durationSeconds,
      trafficDurationSeconds,
      routeGeometry: "mock_google_encoded_polyline_changa_expressway",
      startLocation: options.origin,
      destination: options.destination,
      provider: "google",
      timestamp: new Date().toISOString(),
      summary: {
        formattedDistance: `${distKm.toFixed(1)} km`,
        formattedDuration: `${Math.round(trafficDurationSeconds / 60)} min`,
        formattedTrafficDelay: trafficDelaySeconds > 0 ? `+${Math.round(trafficDelaySeconds / 60)} min` : "None",
        congestionLevel: trafficDelaySeconds > 600 ? "heavy" : trafficDelaySeconds > 0 ? "moderate" : "low",
      },
      steps: [
        {
          instruction: "Head south on Highway toward CHARUSAT Campus",
          distanceMeters: 12000,
          durationSeconds: 720,
          startLocation: options.origin,
          endLocation: options.destination,
        },
        {
          instruction: "Take expressway exit toward Changa",
          distanceMeters: 22200,
          durationSeconds: 1560,
          startLocation: options.origin,
          endLocation: options.destination,
        },
      ],
    };
  }

  async estimateDurationSeconds(options: RouteRequestOptions): Promise<{
    durationSeconds: number;
    trafficDurationSeconds: number;
    distanceMeters: number;
  }> {
    const route = await this.calculateRoute(options);
    return {
      durationSeconds: route.durationSeconds,
      trafficDurationSeconds: route.trafficDurationSeconds,
      distanceMeters: route.distanceMeters,
    };
  }
}
