import { MapProviderRegistry } from "./MapRegistry";
import { GeoPoint, RouteRequestOptions } from "../models/types";
import { RouteResult } from "../models/RouteResult";
import { GeocodingResult, PlaceAutocompletePrediction } from "../models/GeocodingResult";
import { TrafficResult } from "../models/TrafficResult";

/**
 * MapDomainService.
 * Pure Domain Service consumed by UI components, Zustand stores, and the future ETA Engine.
 * Operates exclusively on normalized domain models (RouteResult, GeocodingResult, TrafficResult).
 * Completely unaware of whether Google Maps or Mapbox fulfills the operation.
 */
export class MapDomainService {
  private static instance: MapDomainService | null = null;
  private registry = MapProviderRegistry.getInstance();

  public static getInstance(): MapDomainService {
    if (!this.instance) {
      this.instance = new MapDomainService();
    }
    return this.instance;
  }

  /**
   * Computes normalized route and traffic travel budget for dynamic alarm calculation.
   */
  async calculateCommuteRoute(options: RouteRequestOptions): Promise<RouteResult> {
    const routingProvider = this.registry.getRoutingProvider();
    return await routingProvider.calculateRoute(options);
  }

  /**
   * Forward geocodes an address or query to GPS coordinates.
   */
  async searchAddress(query: string): Promise<GeocodingResult[]> {
    const geocodingProvider = this.registry.getGeocodingProvider();
    return await geocodingProvider.geocode(query);
  }

  /**
   * Reverse geocodes GPS coordinates into a human-readable location address.
   */
  async reverseGeocode(point: GeoPoint): Promise<GeocodingResult | null> {
    const geocodingProvider = this.registry.getGeocodingProvider();
    return await geocodingProvider.reverseGeocode(point);
  }

  /**
   * Autocompletes destination query suggestions.
   */
  async getAutocompleteSuggestions(input: string): Promise<PlaceAutocompletePrediction[]> {
    const geocodingProvider = this.registry.getGeocodingProvider();
    return await geocodingProvider.autocomplete(input);
  }

  /**
   * Retrieves real-time traffic slowdown and incidents along a route corridor.
   */
  async getCorridorTraffic(origin: GeoPoint, destination: GeoPoint): Promise<TrafficResult> {
    const trafficProvider = this.registry.getTrafficProvider();
    return await trafficProvider.getTrafficConditions(origin, destination);
  }
}

export const mapDomainService = MapDomainService.getInstance();
