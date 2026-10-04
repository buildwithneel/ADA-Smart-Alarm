import { GeoPoint } from "../models/types";
import { TrafficResult } from "../models/TrafficResult";

/**
 * Common Traffic Provider Contract.
 * Abstracts real-time road conditions, traffic slowdowns, and road hazards.
 */
export interface ITrafficProvider {
  readonly name: "google" | "mapbox";

  /**
   * Retrieves live traffic conditions along a corridor between two coordinates.
   */
  getTrafficConditions(origin: GeoPoint, destination: GeoPoint): Promise<TrafficResult>;
}
