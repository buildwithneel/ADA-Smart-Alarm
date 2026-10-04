import { GeoPoint } from "../models/types";
import { GeocodingResult, PlaceAutocompletePrediction } from "../models/GeocodingResult";

/**
 * Common Geocoding Provider Contract.
 * Abstracts forward geocoding, reverse geocoding, and autocomplete predictions.
 */
export interface IGeocodingProvider {
  readonly name: "google" | "mapbox";

  /**
   * Forward Geocoding: Converts an address/query string into GPS coordinates.
   */
  geocode(addressQuery: string): Promise<GeocodingResult[]>;

  /**
   * Reverse Geocoding: Converts GPS coordinates into a human-readable address.
   */
  reverseGeocode(point: GeoPoint): Promise<GeocodingResult | null>;

  /**
   * Autocomplete: Returns suggested place predictions for search inputs.
   */
  autocomplete(input: string): Promise<PlaceAutocompletePrediction[]>;
}
