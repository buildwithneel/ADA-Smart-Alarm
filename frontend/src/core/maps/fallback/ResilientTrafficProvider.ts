import { ITrafficProvider } from "../interfaces/ITrafficProvider";
import { GeoPoint } from "../models/types";
import { TrafficResult } from "../models/TrafficResult";

/**
 * Resilient Traffic Fallback Decorator.
 */
export class ResilientTrafficProvider implements ITrafficProvider {
  readonly name: "google" | "mapbox";

  constructor(
    private readonly primary: ITrafficProvider,
    private readonly fallback: ITrafficProvider,
    private readonly enableFallback: boolean = true
  ) {
    this.name = primary.name;
  }

  async getTrafficConditions(origin: GeoPoint, destination: GeoPoint): Promise<TrafficResult> {
    try {
      return await this.primary.getTrafficConditions(origin, destination);
    } catch (err) {
      if (!this.enableFallback) throw err;
      console.warn(`[ADA Traffic Fallback] Primary traffic query failed. Invoking fallback.`);
      return await this.fallback.getTrafficConditions(origin, destination);
    }
  }
}
