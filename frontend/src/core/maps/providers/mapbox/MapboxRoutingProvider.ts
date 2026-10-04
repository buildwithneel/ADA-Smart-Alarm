import { IRoutingProvider } from "../../interfaces/IRoutingProvider";
import { RouteRequestOptions } from "../../models/types";
import { RouteResult } from "../../models/RouteResult";

/**
 * Mapbox Directions API (with Mapbox Traffic profile) implementation.
 *
 * [INTEGRATION HOOK - STEP 3/4]:
 * In real implementation: calls Mapbox Directions API:
 * `GET https://api.mapbox.com/directions/v5/mapbox/driving-traffic/${origin.lng},${origin.lat};${dest.lng},${dest.lat}?access_token=${token}&geometries=geojson&steps=true`
 */
export class MapboxRoutingProvider implements IRoutingProvider {
  readonly name = "mapbox" as const;

  constructor(public readonly accessToken?: string) {}

  async calculateRoute(options: RouteRequestOptions): Promise<RouteResult> {
    const profileSpeed = {
      driving: 44,
      transit: 28,
      bicycling: 15,
      walking: 4.5,
    }[options.transportMode];

    const distKm = 34.2;
    const distanceMeters = Math.round(distKm * 1000);
    const durationSeconds = Math.round((distKm / profileSpeed) * 3600);
    const trafficDelaySeconds = options.transportMode === "driving" ? 420 : 0; // +7 min traffic
    const trafficDurationSeconds = durationSeconds + trafficDelaySeconds;

    return {
      distanceMeters,
      durationSeconds,
      trafficDurationSeconds,
      routeGeometry: JSON.stringify({
        type: "LineString",
        coordinates: [
          [options.origin.longitude, options.origin.latitude],
          [options.destination.longitude, options.destination.latitude],
        ],
      }),
      startLocation: options.origin,
      destination: options.destination,
      provider: "mapbox",
      timestamp: new Date().toISOString(),
      summary: {
        formattedDistance: `${distKm.toFixed(1)} km`,
        formattedDuration: `${Math.round(trafficDurationSeconds / 60)} min`,
        formattedTrafficDelay: trafficDelaySeconds > 0 ? `+${Math.round(trafficDelaySeconds / 60)} min` : "None",
        congestionLevel: trafficDelaySeconds > 600 ? "heavy" : trafficDelaySeconds > 0 ? "moderate" : "low",
      },
      steps: [
        {
          instruction: "Depart south via Highway toward Changa",
          distanceMeters: 14000,
          durationSeconds: 840,
          startLocation: options.origin,
          endLocation: options.destination,
        },
        {
          instruction: "Follow campus connector to CHARUSAT main gate",
          distanceMeters: 20200,
          durationSeconds: 1440,
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
