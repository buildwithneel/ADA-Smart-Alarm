import { RouteRequestOptions } from "../models/types";
import { RouteResult } from "../models/RouteResult";

/**
 * Common Routing & Directions Provider Contract.
 * Consumed by ETA calculations without dependency on Google Routes or Mapbox Directions API.
 */
export interface IRoutingProvider {
  readonly name: "google" | "mapbox";

  /**
   * Computes the optimal route factoring in distance, mode, and traffic delay.
   */
  calculateRoute(options: RouteRequestOptions): Promise<RouteResult>;

  /**
   * Fast matrix estimate between origin and destination.
   */
  estimateDurationSeconds(options: RouteRequestOptions): Promise<{
    durationSeconds: number;
    trafficDurationSeconds: number;
    distanceMeters: number;
  }>;
}
