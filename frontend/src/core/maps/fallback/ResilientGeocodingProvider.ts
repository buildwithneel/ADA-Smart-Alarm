import { IGeocodingProvider } from "../interfaces/IGeocodingProvider";
import { GeoPoint } from "../models/types";
import { GeocodingResult, PlaceAutocompletePrediction } from "../models/GeocodingResult";

/**
 * Resilient Geocoding Fallback Decorator.
 */
export class ResilientGeocodingProvider implements IGeocodingProvider {
  readonly name: "google" | "mapbox";

  constructor(
    private readonly primary: IGeocodingProvider,
    private readonly fallback: IGeocodingProvider,
    private readonly enableFallback: boolean = true
  ) {
    this.name = primary.name;
  }

  async geocode(addressQuery: string): Promise<GeocodingResult[]> {
    try {
      return await this.primary.geocode(addressQuery);
    } catch (err) {
      if (!this.enableFallback) throw err;
      console.warn(`[ADA Geocoding Fallback] Primary geocoding failed. Invoking fallback.`);
      return await this.fallback.geocode(addressQuery);
    }
  }

  async reverseGeocode(point: GeoPoint): Promise<GeocodingResult | null> {
    try {
      return await this.primary.reverseGeocode(point);
    } catch (err) {
      if (!this.enableFallback) throw err;
      console.warn(`[ADA Geocoding Fallback] Primary reverse geocode failed. Invoking fallback.`);
      return await this.fallback.reverseGeocode(point);
    }
  }

  async autocomplete(input: string): Promise<PlaceAutocompletePrediction[]> {
    try {
      return await this.primary.autocomplete(input);
    } catch (err) {
      if (!this.enableFallback) throw err;
      return await this.fallback.autocomplete(input);
    }
  }
}
